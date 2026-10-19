import cv2
import numpy as np
import os
import time
from picamera2 import Picamera2

btn_action = None

def mouse_callback(event, x, y, flags, param):
    """Fångar upp touch-tryck direkt på 7"-pekskärmen."""
    global btn_action
    if event == cv2.EVENT_LBUTTONDOWN:
        btn_action = (x, y)

def draw_button(img, pt1, pt2, text, bg_color, text_color=(255, 255, 255)):
    """Ritar en stilren touchknapp med mjuk kant och centrerad text."""
    cv2.rectangle(img, pt1, pt2, bg_color, -1)
    cv2.rectangle(img, pt1, pt2, (200, 200, 200), 1)
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.55
    thickness = 1
    (t_w, t_h), _ = cv2.getTextSize(text, font, scale, thickness)
    tx = pt1[0] + (pt2[0] - pt1[0] - t_w) // 2
    ty = pt1[1] + (pt2[1] - pt1[1] + t_h) // 2
    cv2.putText(img, text, (tx, ty), font, scale, text_color, thickness, cv2.LINE_AA)

def auto_adapt_environment(img_bgr):
    b_mean = np.mean(img_bgr[:, :, 0])
    g_mean = np.mean(img_bgr[:, :, 1])
    r_mean = np.mean(img_bgr[:, :, 2])

    gray_target = (b_mean + g_mean + r_mean) / 3.0

    if b_mean == 0 or g_mean == 0 or r_mean == 0:
        return img_bgr

    scale_b = gray_target / b_mean
    scale_g = gray_target / g_mean
    scale_r = gray_target / r_mean

    img_float = img_bgr.astype(np.float32)
    img_float[:, :, 0] *= scale_b
    img_float[:, :, 1] *= scale_g
    img_float[:, :, 2] *= scale_r

    return np.clip(img_float, 0, 255).astype(np.uint8)

def standardize_brightness(crop_img, target_mean=180.0):
    current_mean = np.mean(crop_img)
    if current_mean <= 10.0:
        return crop_img

    scale = target_mean / current_mean
    return np.clip(crop_img.astype(np.float32) * scale, 0, 255).astype(np.uint8)

def main():
    global btn_action
    print("Startar hudscanner i spegelvänt läge med touchknappar...")
    
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"size": (1280, 720), "format": "XBGR8888"})
    picam2.configure(config)
    picam2.start()

    picam2.set_controls({
        "AfMode": 2,          
        "AeEnable": True,     
        "AwbEnable": True     
    })

    window_name = "Hudscanner"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.setMouseCallback(window_name, mouse_callback)

    focus_locked = False 
    is_frozen = False
    frozen_display = None
    frozen_crop = None

    logging_active = False
    last_log_time = 0
    log_interval = 4.0
    log_filename = "rgb_log.txt"

    try:
        while True:
            frame = picam2.capture_array()
            key = cv2.waitKey(1) & 0xFF

            # Avläs eventuellt tryck på pekskärmen
            click_x, click_y = (-1, -1)
            if btn_action is not None:
                click_x, click_y = btn_action
                btn_action = None

            if not is_frozen:
                # ------------------------------------------
                # LIVE-LÄGE
                # ------------------------------------------
                if frame.shape[2] == 4:
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                else:
                    frame_bgr = frame.copy()

                # Spegelvänd bilden horisontellt (1 = spegelvänd vänster/höger)
                frame_bgr = cv2.flip(frame_bgr, 1)

                frame_bgr = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                frame_corrected = auto_adapt_environment(frame_bgr)

                h, w = frame_corrected.shape[:2]
                cx, cy = w // 2, h // 2
                box_size = 112
                
                mole_crop = frame_corrected[cy-box_size : cy+box_size, cx-box_size : cx+box_size]

                current_time = time.time()
                if logging_active and (current_time - last_log_time >= log_interval):
                    last_log_time = current_time
                    timestamp = time.strftime("%H:%M:%S")
                    r_val = int(np.mean(mole_crop[:, :, 0]))
                    g_val = int(np.mean(mole_crop[:, :, 1]))
                    b_val = int(np.mean(mole_crop[:, :, 2]))
                    with open(log_filename, "a") as f:
                        f.write(f"[{timestamp}] R: {r_val:<3} | G: {g_val:<3} | B: {b_val:<3}\n")

                display_frame = frame_corrected.copy()

                # Centrerad mätram för fläcken
                cv2.rectangle(display_frame, (cx-box_size, cy-box_size), (cx+box_size, cy+box_size), (0, 255, 0), 2)

                # Placering av touchknappar längst ner
                btn_y1 = h - 65
                btn_y2 = h - 15

                # Knapp 1: Fokus (Auto/Låst)
                b1_x1, b1_x2 = 25, 225
                focus_color = (40, 140, 40) if not focus_locked else (40, 40, 180)
                focus_text = "Fokus: AUTO" if not focus_locked else "Fokus: LAST"
                draw_button(display_frame, (b1_x1, btn_y1), (b1_x2, btn_y2), focus_text, focus_color)

                # Knapp 2: Frys bild
                b2_x1, b2_x2 = (w // 2) - 100, (w // 2) + 100
                draw_button(display_frame, (b2_x1, btn_y1), (b2_x2, btn_y2), "FRYS BILD", (180, 100, 30))

                # Knapp 3: Avsluta
                b3_x1, b3_x2 = w - 180, w - 25
                draw_button(display_frame, (b3_x1, btn_y1), (b3_x2, btn_y2), "AVSLUTA", (40, 40, 180))

                cv2.imshow(window_name, display_frame)

                # Hantera touchklick
                if btn_y1 <= click_y <= btn_y2:
                    if b1_x1 <= click_x <= b1_x2:
                        key = ord('f')
                    elif b2_x1 <= click_x <= b2_x2:
                        key = ord(' ')
                    elif b3_x1 <= click_x <= b3_x2:
                        key = ord('q')

                if key == ord(' '):  
                    is_frozen = True
                    frozen_display = frame_corrected.copy()
                    frozen_crop = mole_crop.copy()
                
                elif key == ord('f'):
                    focus_locked = not focus_locked
                    picam2.set_controls({"AfMode": 0 if focus_locked else 2})

                elif key == ord('l'):
                    logging_active = not logging_active

                elif key == ord('q'):
                    break

            else:
                # ------------------------------------------
                # FRYST LÄGE
                # ------------------------------------------
                show_freeze = frozen_display.copy()
                h, w = show_freeze.shape[:2]
                cx, cy = w // 2, h // 2
                box_size = 112

                cv2.rectangle(show_freeze, (cx-box_size, cy-box_size), (cx+box_size, cy+box_size), (0, 255, 255), 2)
                cv2.putText(show_freeze, "BILD FRYST - GRANSKNING", (cx-130, cy-box_size-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                btn_y1 = h - 65
                btn_y2 = h - 15

                # Knapp 1: Avbryt
                b_redo_x1, b_redo_x2 = 25, 225
                draw_button(show_freeze, (b_redo_x1, btn_y1), (b_redo_x2, btn_y2), "AVBRYT", (60, 60, 60))

                # Knapp 2: Spara med målnivå 180
                b_save_x1, b_save_x2 = (w // 2) - 100, (w // 2) + 100
                draw_button(show_freeze, (b_save_x1, btn_y1), (b_save_x2, btn_y2), "SPARA (L=180)", (35, 145, 35))

                # Knapp 3: Avsluta
                b_exit_x1, b_exit_x2 = w - 180, w - 25
                draw_button(show_freeze, (b_exit_x1, btn_y1), (b_exit_x2, btn_y2), "AVSLUTA", (40, 40, 180))

                cv2.imshow(window_name, show_freeze)

                if btn_y1 <= click_y <= btn_y2:
                    if b_redo_x1 <= click_x <= b_redo_x2:
                        key = ord('a')
                    elif b_save_x1 <= click_x <= b_save_x2:
                        key = ord('s')
                    elif b_exit_x1 <= click_x <= b_exit_x2:
                        key = ord('q')

                if key == ord('s'):  
                    normalized_image = standardize_brightness(frozen_crop, target_mean=180.0)

                    counter = 1
                    while os.path.exists(f"leverflack-{counter}.jpg"):
                        counter += 1
                    
                    filename = f"leverflack-{counter}.jpg"
                    cv2.imwrite(filename, normalized_image)
                    print(f"📸 SPARAD: {filename}")
                    
                    flash = np.ones_like(show_freeze) * 255
                    cv2.imshow(window_name, flash)
                    cv2.waitKey(100)
                    is_frozen = False
                    
                elif key == ord('a'):
                    is_frozen = False
                    
                elif key == ord('q'):
                    break

    finally:
        picam2.stop()
        cv2.destroyAllWindows()
        print("Program och skärm avslutade.")

if __name__ == "__main__":
    main()
