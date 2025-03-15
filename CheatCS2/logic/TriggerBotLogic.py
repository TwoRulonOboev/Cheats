import pymem
import pymem.process
import requests
import win32api
import win32con
import time
import random
from src.utils.OffsetsManager import OffsetsManager

class TriggerBot:
    def __init__(self, random_delay=110, min_delay=240, key_bind=ord("X"), attack_all=False):
        self.random_delay = random_delay
        self.min_delay = min_delay
        self.key_bind = key_bind
        self.attack_all = attack_all
        
        self.pm = pymem.Pymem("cs2.exe")
        self.client = pymem.process.module_from_name(self.pm.process_handle, "client.dll").lpBaseOfDll
        self.offsets = self._get_merged_offsets()

    def _get_merged_offsets(self):
        offsets = OffsetsManager.get_offsets()
        client_dll = OffsetsManager.get_client_dll()
        
        return {
            'dwEntityList': offsets['client.dll']['dwEntityList'],
            'dwLocalPlayerPawn': offsets['client.dll']['dwLocalPlayerPawn'],
            'm_iTeamNum': client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_iTeamNum'],
            'm_iHealth': client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_iHealth'],
            'm_iIDEntIndex': client_dll['client.dll']['classes']['C_CSPlayerPawnBase']['fields']['m_iIDEntIndex']
        }

    def run(self):
        while True:
            try:
                # Проверка состояния клавиши через GetKeyState
                if win32api.GetKeyState(self.key_bind) < 0:
                    player = self.pm.read_longlong(self.client + self.offsets['dwLocalPlayerPawn'])
                    entityId = self.pm.read_int(player + self.offsets['m_iIDEntIndex'])
                    
                    if entityId > 0:
                        entList = self.pm.read_longlong(self.client + self.offsets['dwEntityList'])
                        entEntry = self.pm.read_longlong(entList + 0x8 * ((entityId & 0x7FFF) >> 9) + 0x10)
                        entity = self.pm.read_longlong(entEntry + 120 * (entityId & 0x1FF))
                        
                        if entity:
                            entityTeam = self.pm.read_int(entity + self.offsets['m_iTeamNum'])
                            playerTeam = self.pm.read_int(player + self.offsets['m_iTeamNum'])
                            
                            if self.attack_all or entityTeam != playerTeam:
                                entityHp = self.pm.read_int(entity + self.offsets['m_iHealth'])
                                
                                if entityHp > 0:
                                    delay_in = random.randint(self.min_delay, self.min_delay + self.random_delay)
                                    time.sleep(delay_in / 1000)  # Исправлено деление на 1000 вместо 10000
                                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
                                    
                                    delay_out = random.randint(self.min_delay, self.min_delay + self.random_delay)
                                    time.sleep(delay_out / 1000)  # Исправлено деление
                                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
            except Exception as e:
                print(f"TriggerBot error: {str(e)}")
                time.sleep(1)