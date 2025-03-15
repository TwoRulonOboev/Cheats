import pymem
import pymem.process
import time
import imgui
from src.utils.OffsetsManager import OffsetsManager

class ESP:
    def __init__(self, window_width, window_height, **settings):
        self.window_width = window_width
        self.window_height = window_height
        
        # Настройки из Main
        self.settings = settings
        self.colors = {
            'visible_box': settings.get('visible_box_color', (0, 0, 1, 1)),
            'hidden_box': settings.get('hidden_box_color', (1, 0, 0, 1)),
            'hp_bar': settings.get('hp_bar_color', (0, 1, 0, 1))
        }

        self.pm = None
        self.client = None
        self.offsets = OffsetsManager.get_offsets()
        self.client_dll = OffsetsManager.get_client_dll()
        
        self.initialize_memory()

    def initialize_memory(self):
        while True:
            time.sleep(1)
            try:
                self.pm = pymem.Pymem("cs2.exe")
                self.client = pymem.process.module_from_name(
                    self.pm.process_handle, "client.dll").lpBaseOfDll
                break
            except:
                pass

    def w2s(self, mtx, posx, posy, posz):
        screenW = (mtx[12] * posx) + (mtx[13] * posy) + (mtx[14] * posz) + mtx[15]

        if screenW > 0.001:
            screenX = (mtx[0] * posx) + (mtx[1] * posy) + (mtx[2] * posz) + mtx[3]
            screenY = (mtx[4] * posx) + (mtx[5] * posy) + (mtx[6] * posz) + mtx[7]

            camX = self.window_width / 2
            camY = self.window_height / 2

            x = camX + (camX * screenX / screenW) // 1
            y = camY - (camY * screenY / screenW) // 1

            return [x, y]
        return [-999, -999]

    def render(self, draw_list):
        if not self.pm or not self.client:
            return

        try:
            view_matrix = [self.pm.read_float(self.client + self.offsets['client.dll']['dwViewMatrix'] + i*4) 
                         for i in range(16)]
            local_player_pawn = self.pm.read_longlong(self.client + self.offsets['client.dll']['dwLocalPlayerPawn'])
            local_team = self.pm.read_int(local_player_pawn + self.client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_iTeamNum'])
        except:
            return

        for i in range(1, 64):
            try:
                entity = self.pm.read_longlong(self.client + self.offsets['client.dll']['dwEntityList'])
                list_entry = self.pm.read_longlong(entity + ((8 * (i & 0x7FFF) >> 9) + 16))
                controller = self.pm.read_longlong(list_entry + 120 * (i & 0x1FF))
                
                pawn_handle = self.pm.read_uint(controller + self.client_dll['client.dll']['classes']['CCSPlayerController']['fields']['m_hPlayerPawn'])
                pawn_entry = self.pm.read_longlong(entity + (0x8 * ((pawn_handle & 0x7FFF) >> 9) + 16))
                entity_pawn = self.pm.read_longlong(pawn_entry + 120 * (pawn_handle & 0x1FF))
                
                if entity_pawn == local_player_pawn or self.pm.read_int(entity_pawn + 
                    self.client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_lifeState']) != 256:
                    continue
                
                # Проверка видимости
                is_spotted = self.pm.read_bool(entity_pawn + 
                    self.client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_bSpotted'])
                entity_team = self.pm.read_int(entity_pawn + 
                    self.client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_iTeamNum'])
                
                if entity_team == local_team and not self.settings.get('show_teammates', False):
                    continue
                
                # Выбор цвета
                box_color = imgui.get_color_u32_rgba(*self.colors['visible_box']) if is_spotted else \
                         imgui.get_color_u32_rgba(*self.colors['hidden_box'])
                hp_color = imgui.get_color_u32_rgba(*self.colors['hp_bar'])

                # Логика отрисовки
                game_scene = self.pm.read_longlong(entity_pawn + 
                    self.client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_pGameSceneNode'])
                bone_matrix = self.pm.read_longlong(game_scene + 
                    self.client_dll['client.dll']['classes']['CSkeletonInstance']['fields']['m_modelState'] + 0x80)
                
                head_pos = self.w2s(view_matrix, 
                    self.pm.read_float(bone_matrix + 6*0x20), 
                    self.pm.read_float(bone_matrix + 6*0x20 + 4), 
                    self.pm.read_float(bone_matrix + 6*0x20 + 8) + 8)
                
                feet_pos = self.w2s(view_matrix, 
                    self.pm.read_float(bone_matrix + 28*0x20), 
                    self.pm.read_float(bone_matrix + 28*0x20 + 4), 
                    self.pm.read_float(bone_matrix + 28*0x20 + 8))
                
                height = abs(head_pos[1] - feet_pos[1])
                width = height * 0.4
                
                # Рисуем бокс
                draw_list.add_rect(
                    head_pos[0] - width/2, head_pos[1],
                    head_pos[0] + width/2, feet_pos[1],
                    box_color, thickness=2
                )
                
                # Рисуем HP-бар
                if self.settings.get('hp_bar', True):
                    hp = self.pm.read_int(entity_pawn + 
                        self.client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_iHealth'])
                    hp_width = (hp / 100) * width
                    
                    draw_list.add_rect_filled(
                        head_pos[0] - width/2 - 3, feet_pos[1] + 2,
                        head_pos[0] - width/2 - 1, feet_pos[1] - height - 2,
                        imgui.get_color_u32_rgba(0, 0, 0, 0.5)
                    )
                    draw_list.add_rect_filled(
                        head_pos[0] - width/2 - 3, feet_pos[1] + 2 - (height * (hp/100)),
                        head_pos[0] - width/2 - 1, feet_pos[1] + 2,
                        hp_color
                    )
                    
            except:
                continue