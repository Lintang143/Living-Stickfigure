#!/usr/bin/env python3
import os
import sys
import math
import random
import pygame
from groq import Groq
from duckduckgo_search import DDGS

# --- INITIALIZATION & CONFIG ---
pygame.init()
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Animator vs Stickman AI - Fixed Spawn State")
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY_PANEL = (220, 220, 220)
GRAY_HOVER = (190, 190, 190)
BLUE_ACT = (30, 144, 255)
RED = (255, 50, 50)
GREEN = (50, 205, 50)

# Fonts
FONT_S = pygame.font.SysFont("Arial", 12)
FONT_M = pygame.font.SysFont("Arial", 14)
FONT_L = pygame.font.SysFont("Arial", 18)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# --- DATA CONFIG STRUCTURE ---
class StickmanConfig:
    def __init__(self):
        self.filename = "my_stickman"
        self.powerLevel = 5
        self.speed = 10
        self.health = 100
        # Traits
        self.thinking = True
        self.anger = False  
        self.curiosity = True
        self.selfPreservation = True
        self.make_alive = False  # <-- SEKARANG DEFAULT-NYA MATI (DIAM KAKU)

# --- AI BRAIN ---
class GroqBrain:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

    def ask_stickman(self, cfg: StickmanConfig, prompt: str) -> str:
        if not self.client: return "GROQ_KEY_MISSING"
        
        sifat = []
        if cfg.anger: sifat.append("Pemarah/Agresif/Suka Menyerang")
        if cfg.curiosity: sifat.append("Penuh Rasa Ingin Tahu")
        
        sys_prompt = (
            f"Kamu adalah stickman hidup di kanvas gambar bernama {cfg.filename}. "
            f"Sifatmu: {', '.join(sifat if sifat else ['Baik/Tenang'])}. "
            f"Kamu berbicara langsung di kanvas menggunakan text tool. JAWAB DENGAN SANGAT SINGKAT (Maksimal 10 kata)!"
        )
        try:
            comp = self.client.chat.completions.create(
                messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
                model="llama3-8b-8192", temperature=0.7
            )
            return comp.choices[0].message.content
        except:
            return "..."

ai_brain = GroqBrain()

# --- LIVING STICKMAN WITH SMOOTH PHYSICS ---
class LivingStickman:
    def __init__(self, x, y, cfg: StickmanConfig):
        self.x = x
        self.y = y
        self.cfg = cfg
        self.max_health = cfg.health
        self.health = cfg.health
        self.alive = cfg.make_alive
        self.timer = 0
        
        # Physics & Inertia Vectors
        self.vx = 0
        self.vy = 0
        self.target_vx = 0
        self.target_vy = 0
        self.friction = 0.85  
        self.acceleration = 0.2
        
        # Communication Bubble via Text Tool
        self.speech_text = ""
        self.speech_timer = 0
        self.speech_pos = (0, 0)

    def update(self, mouse_pos, mouse_pressed, current_tool):
        self.timer += 1
        if not self.alive: 
            # Jika mati, paksa semua kecepatan jadi nol agar diam kaku
            self.vx = 0
            self.vy = 0
            self.target_vx = 0
            self.target_vy = 0
            if self.speech_timer > 0: self.speech_timer -= 1
            return

        # Hitung Jarak ke Kursor Mouse
        dx = mouse_pos[0] - self.x
        dy = mouse_pos[1] - self.y
        dist = math.hypot(dx, dy)

        # 1. BRAIN & PHYSICS LOGIC (Dinamis Berdasarkan Sifat)
        if self.cfg.anger:
            if dist > 15:
                self.target_vx = (dx / dist) * self.cfg.speed
                self.target_vy = (dy / dist) * self.cfg.speed
            else:
                self.target_vx = 0
                self.target_vy = 0

            # Mode Pertarungan Jarak Dekat
            if dist < 45:
                if mouse_pressed[0] and current_tool in ["BRUSH", "FILL"]:
                    self.health -= 0.8  
                    if self.timer % 15 == 0:
                        self.speech_text = random.choice(["Woi! Sakit!", "Jangan coret aku!", "Gak kena!"])
                        self.speech_timer = 30
                        self.speech_pos = (self.x + 20, self.y - 45)
                else:
                    if self.timer % 30 == 0:
                        self.speech_text = random.choice(["AMBIL INI!", "SERANG!", "Hancurkan Kursor!"])
                        self.speech_timer = 25
                        self.speech_pos = (self.x + 20, self.y - 45)
        else:
            # Jika BAIK: Pergerakan santai acak (Wandering Mode)
            if self.timer % 60 == 0:
                self.target_vx = random.choice([-3, -1, 1, 3])
                self.target_vy = random.choice([-3, -1, 1, 3])

            if self.x < 130 or self.x > WIDTH - 40: self.target_vx *= -1
            if self.y < 60 or self.y > HEIGHT - 40: self.target_vy *= -1

        # Penerapan Hukum Fisika (Inersia & Gesekan Jaringan)
        self.vx += (self.target_vx - self.vx) * self.acceleration
        self.vy += (self.target_vy - self.vy) * self.acceleration
        self.vx *= self.friction
        self.vy *= self.friction

        # Update Posisi Aktual Koordinat
        self.x += self.vx
        self.y += self.vy

        self.x = max(120, min(WIDTH - 40, self.x))
        self.y = max(60, min(HEIGHT - 40, self.y))

        if self.speech_timer > 0: self.speech_timer -= 1
        if self.health <= 0: self.alive = False

    def draw(self, surface):
        speed_factor = math.hypot(self.vx, self.vy)
        
        # --- ALAN BECKER ANIMATION ENGINE ---
        # Efek Kelenturan Tubuh Dinamis (Hanya aktif jika hidup & bergerak)
        stretch_y = math.sin(self.timer * 0.15) * 2 if self.alive else 0
        if self.alive and speed_factor > 1.5:
            tilt = self.vx * 2.0  
            stretch_x = speed_factor * 0.4
        else:
            tilt = 0
            stretch_x = 0

        cx, cy = int(self.x), int(self.y)
        hx, hy = int(cx + tilt), int(cy - 30 + stretch_y) 

        color = RED if self.cfg.anger else BLACK
        thickness = 3 

        # A. Kepala Vektor
        pygame.draw.circle(surface, color, (hx, hy), 11, thickness)
        
        # B. Badan
        pygame.draw.line(surface, color, (hx, hy + 11), (cx, cy + 10), thickness)
        
        # C. Sistem Ayunan Tangan & Kaki Berlari (Run Cycle)
        if self.alive and speed_factor > 1.0:
            swing = math.sin(self.timer * 0.25) * 16
            pygame.draw.line(surface, color, (cx, cy + 2), (int(cx - 15 + swing), int(cy + 14 - swing)), thickness)
            pygame.draw.line(surface, color, (cx, cy + 2), (int(cx + 15 - swing), int(cy + 14 + swing)), thickness)
            
            leg_swing = math.sin(self.timer * 0.25) * 18
            pygame.draw.line(surface, color, (cx, cy + 10), (int(cx - 12 + leg_swing), cy + 35), thickness)
            pygame.draw.line(surface, color, (cx, cy + 10), (int(cx + 12 - leg_swing), cy + 35), thickness)
        else:
            # Posisi Berdiam Diri / Kaku Mati (Idle Mode)
            pygame.draw.line(surface, color, (cx, cy + 2), (cx - 16, cy + 12), thickness)
            pygame.draw.line(surface, color, (cx, cy + 2), (cx + 16, cy + 12), thickness)
            
            pygame.draw.line(surface, color, (cx, cy + 10), (cx - 10, cy + 35), thickness)
            pygame.draw.line(surface, color, (cx, cy + 10), (cx + 10, cy + 35), thickness)

        if self.health < self.max_health and self.alive:
            pygame.draw.rect(surface, RED, (self.x - 20, self.y - 60, 40, 5))
            pygame.draw.rect(surface, GREEN, (self.x - 20, self.y - 60, int(40 * (self.health / self.max_health)), 5))

        if self.speech_timer > 0 and self.speech_text:
            t_surf = FONT_S.render(self.speech_text, True, color)
            surface.blit(t_surf, self.speech_pos)


# --- ENGINE CONTROLLER STATE ---
current_tool = "BRUSH"
canvas_drawings = []
active_stickmen = []
selected_stickman_idx = None

show_context_menu = False
context_menu_pos = None

show_save_modal = False
modal_cfg = StickmanConfig()
adv_settings_expanded = False
input_filename_active = True

canvas_text_inputs = []

# --- MAIN RUNNER LOOP ---
running = True
while running:
    mx, my = pygame.mouse.get_pos()
    m_buttons = pygame.mouse.get_pressed()

    screen.fill(WHITE)

    for p in canvas_drawings:
        pygame.draw.circle(screen, BLACK, p, 3)

    for txt_obj in canvas_text_inputs:
        t_color = BLUE_ACT if txt_obj["active"] else BLACK
        t_surf = FONT_M.render(txt_obj["text"] + ("|" if txt_obj["active"] and pygame.time.get_ticks() % 1000 < 500 else ""), True, t_color)
        screen.blit(t_surf, txt_obj["pos"])

    for idx, stick in enumerate(active_stickmen):
        stick.update((mx, my), m_buttons, current_tool)
        stick.draw(screen)

    # Panel Kiri (Tools Menu)
    pygame.draw.rect(screen, GRAY_PANEL, (0, 0, 100, HEIGHT))
    pygame.draw.line(screen, BLACK, (100, 0), (100, HEIGHT), 2)

    tools = [("BRUSH", 20), ("FILL", 80), ("TEXT", 140), ("STICKMAN", 200)]
    for tool_name, ty in tools:
        btn_rect = pygame.Rect(10, ty, 80, 40)
        if current_tool == tool_name: bg = BLUE_ACT
        elif btn_rect.collidepoint(mx, my): bg = GRAY_HOVER
        else: bg = WHITE
        
        pygame.draw.rect(screen, bg, btn_rect, border_radius=5)
        pygame.draw.rect(screen, BLACK, btn_rect, 1, border_radius=5)
        txt = FONT_M.render(tool_name, True, BLACK if bg != BLUE_ACT else WHITE)
        screen.blit(txt, (btn_rect.x + 10, btn_rect.y + 12))

    if not show_save_modal and not show_context_menu:
        if m_buttons[0] and mx > 100:
            if current_tool == "BRUSH":
                canvas_drawings.append((mx, my))
            elif current_tool == "FILL":
                screen.fill(BLACK)

    if show_context_menu and context_menu_pos:
        cx, cy = context_menu_pos
        del_rect = pygame.Rect(cx, cy, 110, 25)
        save_rect = pygame.Rect(cx, cy + 25, 110, 25)
        pygame.draw.rect(screen, GRAY_PANEL, (cx, cy, 110, 50))
        pygame.draw.rect(screen, BLACK, (cx, cy, 110, 50), 1)
        
        if del_rect.collidepoint(mx, my): pygame.draw.rect(screen, GRAY_HOVER, del_rect)
        if save_rect.collidepoint(mx, my): pygame.draw.rect(screen, GRAY_HOVER, save_rect)
        
        screen.blit(FONT_M.render("Delete Stickman", True, BLACK), (cx + 5, cy + 5))
        screen.blit(FONT_M.render("Save Stickman", True, BLACK), (cx + 5, cy + 30))

    # MODAL MENU SAVE
    if show_save_modal:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 110))
        screen.blit(overlay, (0,0))

        modal_w, modal_h = 400, 450 if adv_settings_expanded else 200
        m_x, m_y = (WIDTH - modal_w) // 2, (HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(m_x, m_y, modal_w, modal_h)
        
        pygame.draw.rect(screen, WHITE, modal_rect, border_radius=8)
        pygame.draw.rect(screen, BLACK, modal_rect, 2, border_radius=8)

        pygame.draw.rect(screen, GRAY_PANEL, (m_x, m_y, modal_w, 35), border_top_left_radius=8, border_top_right_radius=8)
        screen.blit(FONT_L.render("Save Configuration", True, BLACK), (m_x + 15, m_y + 8))

        # Input Box File Name
        screen.blit(FONT_M.render("File Name:", True, BLACK), (m_x + 20, m_y + 60))
        file_box = pygame.Rect(m_x + 110, m_y + 55, 250, 25)
        pygame.draw.rect(screen, GRAY_PANEL if input_filename_active else WHITE, file_box)
        pygame.draw.rect(screen, BLUE_ACT if input_filename_active else BLACK, file_box, 1)
        screen.blit(FONT_M.render(modal_cfg.filename, True, BLACK), (file_box.x + 5, file_box.y + 4))

        # Advanced Settings Expand Box
        adv_header = pygame.Rect(m_x + 20, m_y + 100, 360, 25)
        pygame.draw.rect(screen, GRAY_PANEL, adv_header)
        exp_txt = "[-] Advanced Settings" if adv_settings_expanded else "[+] Advanced Settings"
        screen.blit(FONT_M.render(exp_txt, True, BLACK), (adv_header.x + 10, adv_header.y + 5))

        if adv_settings_expanded:
            # Trait: Anger
            anger_rect = pygame.Rect(m_x + 30, m_y + 140, 18, 18)
            pygame.draw.rect(screen, WHITE, anger_rect)
            pygame.draw.rect(screen, BLACK, anger_rect, 1)
            if modal_cfg.anger:
                pygame.draw.line(screen, RED, (anger_rect.x+2, anger_rect.y+2), (anger_rect.x+14, anger_rect.y+14), 2)
            screen.blit(FONT_M.render("Anger Trait (Enable Combat Mod against Mouse)", True, BLACK), (m_x + 55, m_y + 140))

            # Stat: Speed
            screen.blit(FONT_M.render(f"Speed: {modal_cfg.speed}", True, BLACK), (m_x + 30, m_y + 175))
            pygame.draw.line(screen, BLACK, (m_x + 120, m_y + 182), (m_x + 270, m_y + 182), 2)
            pygame.draw.circle(screen, BLUE_ACT, (m_x + 120 + (modal_cfg.speed * 10), m_y + 182), 6)

            # Checkbox: Make it alive after save
            alive_rect = pygame.Rect(m_x + 30, m_y + 350, 18, 18)
            pygame.draw.rect(screen, WHITE, alive_rect)
            pygame.draw.rect(screen, BLACK, alive_rect, 1)
            if modal_cfg.make_alive:
                pygame.draw.line(screen, GREEN, (alive_rect.x+2, alive_rect.y+2), (alive_rect.x+14, alive_rect.y+14), 2)
            screen.blit(FONT_M.render("Make it alive after save", True, BLACK), (m_x + 55, m_y + 350))

        btn_save = pygame.Rect(m_x + modal_w - 110, m_y + modal_h - 45, 90, 30)
        pygame.draw.rect(screen, BLUE_ACT, btn_save, border_radius=4)
        screen.blit(FONT_M.render("SAVE", True, WHITE), (btn_save.x + 25, btn_save.y + 7))


    # SYSTEM EVENT CAPTURE
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if show_save_modal:
                m_x, m_y = (WIDTH - 400) // 2, (HEIGHT - (450 if adv_settings_expanded else 200)) // 2
                file_box = pygame.Rect(m_x + 110, m_y + 55, 250, 25)
                adv_header = pygame.Rect(m_x + 20, m_y + 100, 360, 25)
                btn_save = pygame.Rect(m_x + 400 - 110, m_y + (450 if adv_settings_expanded else 200) - 45, 90, 30)

                if file_box.collidepoint(mx, my): input_filename_active = True
                else: input_filename_active = False

                if adv_header.collidepoint(mx, my):
                    adv_settings_expanded = not adv_settings_expanded

                if adv_settings_expanded:
                    anger_rect = pygame.Rect(m_x + 30, m_y + 140, 18, 18)
                    alive_rect = pygame.Rect(m_x + 30, m_y + 350, 18, 18)
                    if anger_rect.collidepoint(mx, my): modal_cfg.anger = not modal_cfg.anger
                    if alive_rect.collidepoint(mx, my): modal_cfg.make_alive = not modal_cfg.make_alive
                    if pygame.Rect(m_x + 120, m_y + 175, 150, 15).collidepoint(mx, my):
                        modal_cfg.speed = int((mx - (m_x + 120)) / 10)
                        modal_cfg.speed = max(1, min(15, modal_cfg.speed))

                if btn_save.collidepoint(mx, my):
                    save_path = os.path.expanduser(f"~/Desktop/{modal_cfg.filename}.json")
                    try:
                        import json
                        with open(save_path, "w") as f:
                            json.dump({"alive": modal_cfg.make_alive, "anger": modal_cfg.anger, "speed": modal_cfg.speed}, f)
                    except: pass
                    
                    if selected_stickman_idx is not None:
                        active_stickmen[selected_stickman_idx].cfg = modal_cfg
                        active_stickmen[selected_stickman_idx].alive = modal_cfg.make_alive
                        if modal_cfg.make_alive:
                            active_stickmen[selected_stickman_idx].speech_text = "AKU HIDUP!"
                            active_stickmen[selected_stickman_idx].speech_timer = 40
                            active_stickmen[selected_stickman_idx].speech_pos = (active_stickmen[selected_stickman_idx].x, active_stickmen[selected_stickman_idx].y - 45)
                    
                    show_save_modal = False 
                continue

            if show_context_menu and context_menu_pos:
                cx, cy = context_menu_pos
                del_rect = pygame.Rect(cx, cy, 110, 25)
                save_rect = pygame.Rect(cx, cy + 25, 110, 25)

                if event.button == 1:
                    if del_rect.collidepoint(mx, my) and selected_stickman_idx is not None:
                        active_stickmen.pop(selected_stickman_idx)
                    elif save_rect.collidepoint(mx, my) and selected_stickman_idx is not None:
                        show_save_modal = True
                    show_context_menu = False
                    continue
                else:
                    show_context_menu = False

            if event.button == 1: 
                panel_clicked = False
                for tool_name, ty in tools:
                    if pygame.Rect(10, ty, 80, 40).collidepoint(mx, my):
                        current_tool = tool_name
                        panel_clicked = True
                        for t in canvas_text_inputs: t["active"] = False
                
                if not panel_clicked and mx > 100:
                    if current_tool == "STICKMAN":
                        # MEMBUAT INSTANCE CONFIG BARU KHUSUS YANG BERSTATUS MATI/FALSE
                        new_cfg = StickmanConfig()
                        new_cfg.make_alive = False
                        active_stickmen.append(LivingStickman(mx, my, new_cfg))
                    elif current_tool == "TEXT":
                        active_found = False
                        for t in canvas_text_inputs:
                            if t["active"] and t["text"].strip():
                                active_found = True
                                t["active"] = False
                                if active_stickmen:
                                    target_stick = active_stickmen[0]
                                    reply = ai_brain.ask_stickman(target_stick.cfg, t["text"])
                                    target_stick.speech_text = reply
                                    target_stick.speech_timer = 90
                                    target_stick.speech_pos = (target_stick.x + 20, target_stick.y - 30)
                        
                        if not active_found:
                            canvas_text_inputs.append({"pos": (mx, my), "text": "", "active": True})

            elif event.button == 3: 
                for idx, stick in enumerate(active_stickmen):
                    if math.hypot(mx - stick.x, my - stick.y) < 30:
                        selected_stickman_idx = idx
                        context_menu_pos = (mx, my)
                        show_context_menu = True

        elif event.type == pygame.KEYDOWN:
            if show_save_modal and input_filename_active:
                if event.key == pygame.K_BACKSPACE:
                    modal_cfg.filename = modal_cfg.filename[:-1]
                else:
                    if len(modal_cfg.filename) < 20 and (event.unicode.isalnum() or event.unicode == "_"):
                        modal_cfg.filename += event.unicode
            else:
                for t in canvas_text_inputs:
                    if t["active"]:
                        if event.key == pygame.K_BACKSPACE:
                            t["text"] = t["text"][:-1]
                        elif event.key == pygame.K_RETURN:
                            t["active"] = False
                            if active_stickmen and t["text"].strip():
                                target_stick = active_stickmen[0]
                                reply = ai_brain.ask_stickman(target_stick.cfg, t["text"])
                                target_stick.speech_text = reply
                                target_stick.speech_timer = 120
                                target_stick.speech_pos = (target_stick.x + 20, target_stick.y - 30)
                        else:
                            if len(t["text"]) < 60:
                                t["text"] += event.unicode

    pygame.display.flip()
    clock.tick(60) 

pygame.quit()
sys.exit()
