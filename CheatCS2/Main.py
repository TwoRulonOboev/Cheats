import glfw
import OpenGL.GL as gl
from imgui.integrations.glfw import GlfwRenderer
import win32gui
import win32con
import imgui
import threading
from logic.EspLogic import ESP
from logic.AimLogic import AimLogic
from logic.TriggerBotLogic import TriggerBot

WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080

def main():
    # Настройки аима
    aim_settings = {
        'aim_speed': 1.0,
        'aim_radius': 220,
        'aim_fov': 85,
        'aim_key': 0x43,  # C
        'aim_mode': 1
    }

    # В секции настроек триггербота
    trigger_settings = {
        'random_delay': 110,
        'min_delay': 240,
        'key_bind': ord("X"),  # Конвертируем символ в код
        'attack_all': False
    }

    esp_settings = {
        'esp_rendering': True,
        'show_teammates': False,
        'hp_bar': True,
        'visible_box_color': (0, 0, 1, 1),     # Синий для видимых
        'hidden_box_color': (1, 0, 0, 1),      # Красный для невидимых
        'hp_bar_color': (0, 1, 0, 1)           # Зеленый для HP
    }

    # Инициализация ESP
    esp = ESP(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        **esp_settings
    )

    # Инициализация триггербота
    trigger = TriggerBot(
        **trigger_settings
    )

    # Инициализация модулей
    aim = AimLogic(
        pm=esp.pm,
        client=esp.client,
        offsets=esp.offsets,
        client_dll=esp.client_dll,
        **aim_settings
    )

    # Запуск триггербота в отдельном потоке
    trigger_thread = threading.Thread(target=trigger.run)
    trigger_thread.daemon = True
    trigger_thread.start()

    # Инициализация окна
    if not glfw.init():
        print("Не удалось инициализировать OpenGL")
        exit(1)

    glfw.window_hint(glfw.TRANSPARENT_FRAMEBUFFER, glfw.TRUE)
    window = glfw.create_window(WINDOW_WIDTH, WINDOW_HEIGHT, "Наложение CS2", None, None)
    
    # Настройка стилей окна
    hwnd = glfw.get_win32_window(window)
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME)
    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
    
    ex_style = win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
    
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, -2, -2, 0, 0,
                        win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)

    # Настройка контекста OpenGL
    glfw.make_context_current(window)
    imgui.create_context()
    impl = GlfwRenderer(window)

    # Главный цикл рендеринга
    while not glfw.window_should_close(window):
        glfw.poll_events()
        impl.process_inputs()
        imgui.new_frame()

        # Отрисовка ESP
        imgui.set_next_window_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        imgui.set_next_window_position(0, 0)
        imgui.begin("Overlay", flags=imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | 
                    imgui.WINDOW_NO_SCROLLBAR | imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_BACKGROUND)
        
        draw_list = imgui.get_window_draw_list()
        esp.render(draw_list)
        aim.draw_fov(draw_list)
        imgui.end()

        # Обновление аима
        aim.run_aimbot()

        # Рендеринг
        gl.glClearColor(0, 0, 0, 0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        imgui.render()
        impl.render(imgui.get_draw_data())
        glfw.swap_buffers(window)

    # Завершение работы
    impl.shutdown()
    glfw.terminate()

if __name__ == '__main__':
    main()