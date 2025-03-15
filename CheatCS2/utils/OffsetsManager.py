import requests
import time

class OffsetsManager:
    _offsets = None
    _client_dll = None
    _last_update = 0
    _update_interval = 60  # Обновление каждые 60 секунд

    @classmethod
    def get_offsets(cls):
        cls._update()
        return {
            'client.dll': {
                'dwViewMatrix': cls._offsets['client.dll']['dwViewMatrix'],
                'dwEntityList': cls._offsets['client.dll']['dwEntityList'],
                'dwLocalPlayerPawn': cls._offsets['client.dll']['dwLocalPlayerPawn']
            }
        }

    @classmethod
    def get_client_dll(cls):
        cls._update()
        # Добавление недостающих офсетов
        cls._client_dll['client.dll']['classes']['C_BaseEntity']['fields']['m_bSpotted'] = 0xED0  # Актуальный офсет!
        return cls._client_dll

    @classmethod
    def _update(cls):
        if time.time() - cls._last_update > cls._update_interval or not cls._offsets:
            try:
                cls._offsets = requests.get(
                    'https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json'
                ).json()
                cls._client_dll = requests.get(
                    'https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json'
                ).json()
                cls._last_update = time.time()
            except Exception as e:
                print(f"Ошибка обновления офсетов: {str(e)}")