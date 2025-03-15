import pymem
import math
import win32api
import win32con
import imgui
from utils.OffsetsManager import OffsetsManager

class AimLogic:
    def __init__(self, pm, client, **settings):
        self.pm = pm
        self.client = client
        self.offsets = OffsetsManager.get_offsets()
        self.client_dll = OffsetsManager.get_client_dll()
        
        self.aim_speed = settings.get('aim_speed', 3.5)
        self.aim_radius = settings.get('aim_radius', 100)
        self.aim_fov = settings.get('aim_fov', 35)
        self.aim_key = settings.get('aim_key', 0x43)
        self.aim_mode = settings.get('aim_mode', 1)

        self.targets = []
        self.last_target = None

    def safe_read(self, func, address, default=None):
        try:
            return func(address)
        except (pymem.exception.MemoryReadError, pymem.exception.WinAPIError):
            return default

    def update_targets(self):
        self.targets = []
        if not self.pm or not self.client:
            return

        view_matrix = [self.safe_read(self.pm.read_float, self.client + self.offsets['client.dll']['dwViewMatrix'] + i*4, 0.0) 
                      for i in range(16)]

        local_player = self.safe_read(self.pm.read_longlong, self.client + self.offsets['client.dll']['dwLocalPlayerPawn'])
        if not local_player:
            return

        entity_list = self.safe_read(self.pm.read_longlong, self.client + self.offsets['client.dll']['dwEntityList'])
        if not entity_list:
            return

        for i in range(1, 64):
            try:
                entity_entry = entity_list + 0x8 * ((i & 0x7FFF) >> 9) + 16
                list_entry = self.safe_read(self.pm.read_longlong, entity_entry)
                if not list_entry:
                    continue

                controller = self.safe_read(self.pm.read_longlong, list_entry + 0x78 * (i & 0x1FF))
                if not controller:
                    continue

                pawn_handle = self.safe_read(self.pm.read_uint, 
                    controller + self.client_dll['client.dll']['classes']['CCSPlayerController']['fields']['m_hPlayerPawn'])
                if not pawn_handle:
                    continue

                pawn_entry = entity_list + 0x8 * ((pawn_handle & 0x7FFF) >> 9) + 16
                pawn_list_entry = self.safe_read(self.pm.read_longlong, pawn_entry)
                if not pawn_list_entry:
                    continue

                entity_pawn = self.safe_read(self.pm.read_longlong, pawn_list_entry + 0x78 * (pawn_handle & 0x1FF))
                if not entity_pawn or entity_pawn == local_player:
                    continue

                if self.safe_read(self.pm.read_int, entity_pawn + 
                                 self.client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_lifeState']) != 256:
                    continue

                game_scene = self.safe_read(self.pm.read_longlong, 
                    entity_pawn + self.client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_pGameSceneNode'])
                if not game_scene:
                    continue

                bone_matrix = self.safe_read(self.pm.read_longlong, 
                    game_scene + self.client_dll['client.dll']['classes']['CSkeletonInstance']['fields']['m_modelState'] + 0x80)
                if not bone_matrix:
                    continue

                bone_id = 6 if self.aim_mode == 1 else 4
                try:
                    pos = [
                        self.pm.read_float(bone_matrix + bone_id * 0x20),
                        self.pm.read_float(bone_matrix + bone_id * 0x20 + 0x4),
                        self.pm.read_float(bone_matrix + bone_id * 0x20 + 0x8)
                    ]
                except:
                    continue

                screen_pos = self.world_to_screen(view_matrix, pos)
                if screen_pos:
                    self.targets.append({
                        'entity': entity_pawn,
                        'screen_pos': screen_pos,
                        'world_pos': pos
                    })

            except Exception as e:
                continue

    def world_to_screen(self, view_matrix, pos):
        screen_w = view_matrix[12] * pos[0] + view_matrix[13] * pos[1] + view_matrix[14] * pos[2] + view_matrix[15]
        if screen_w < 0.001:
            return None

        screen_x = (view_matrix[0] * pos[0] + view_matrix[1] * pos[1] + view_matrix[2] * pos[2] + view_matrix[3]) / screen_w
        screen_y = (view_matrix[4] * pos[0] + view_matrix[5] * pos[1] + view_matrix[6] * pos[2] + view_matrix[7]) / screen_w

        return [
            (screen_x * 0.5 + 0.5) * win32api.GetSystemMetrics(0),
            (0.5 - screen_y * 0.5) * win32api.GetSystemMetrics(1)
        ]

    def get_closest_target(self, local_player_pos):
        closest_distance = float('inf')
        closest_target = None
        
        for target in self.targets:
            dx = target['screen_pos'][0] - local_player_pos[0]
            dy = target['screen_pos'][1] - local_player_pos[1]
            distance = math.hypot(dx, dy)
            
            if distance < self.aim_radius and distance < closest_distance:
                closest_distance = distance
                closest_target = target
                
        return closest_target

    def move_mouse(self, target_pos):
        current_x, current_y = win32api.GetCursorPos()
        
        delta_x = target_pos[0] - current_x
        delta_y = target_pos[1] - current_y
        
        if abs(delta_x) < 1 and abs(delta_y) < 1:
            return
        
        smooth_factor = 1 / self.aim_speed
        new_x = current_x + delta_x * smooth_factor
        new_y = current_y + delta_y * smooth_factor
        
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(new_x - current_x), int(new_y - current_y))

    def draw_fov(self, draw_list):
        center_x = win32api.GetSystemMetrics(0) // 2
        center_y = win32api.GetSystemMetrics(1) // 2
        draw_list.add_circle(center_x, center_y, self.aim_radius, imgui.get_color_u32_rgba(1, 0, 0, 1), thickness=2)

    def run_aimbot(self):
        if win32api.GetAsyncKeyState(self.aim_key) < 0:
            self.update_targets()
            center = (win32api.GetSystemMetrics(0) // 2, win32api.GetSystemMetrics(1) // 2)
            closest = self.get_closest_target(center)
            
            if closest:
                self.move_mouse(closest['screen_pos'])
