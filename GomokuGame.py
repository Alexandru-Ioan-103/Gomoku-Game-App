import pygame
import sys
import random
import os

# ==========================================
# GOMOKU (RENJU) - REGULI PE SCURT
# ==========================================
# Scopul jocului e simplu: fii primul care aliniază 5 piese (orizontal, vertical, diagonal).
# Totuși, pentru că jucătorul care începe (Negrul) are un avantaj matematic uriaș,
# am implementat câteva reguli din varianta competițională (Renju) și deschiderea Swap2:
# 1. Overline: Negrul trebuie să facă FIX 5 piese. Dacă face 6+, pierde (Foul). Albul câștigă cu 5 sau 6+.
# 2. Double-Four: Negrul nu are voie să creeze două linii deschise de 4 piese în același timp.
# 3. Swap2: Primul jucător pune 3 piese pe tablă, iar al doilea decide cu ce culoare vrea să continue.
#
# Detalii oficiale aici:
# https://en.wikipedia.org/wiki/Gomoku
# https://en.wikipedia.org/wiki/Renju
# ==========================================

# Setam dimensiunile tablei si ale ferestrei. N = 15 e standardul pentru Gomoku.
N = 15
DIM = 40
MARGINE = 50
WIDTH = N * DIM + 2 * MARGINE
HEIGHT = N * DIM + 2 * MARGINE

# O paleta de culori aleasa special ca sa dea un vibe de tabla de joc fizica, de lemn.
CUL_FUNDAL = (245, 240, 225)
CUL_GRID = (80, 60, 40)
CUL_NEGRU = (40, 30, 20)
CUL_ALB = (250, 250, 250)
CUL_TEXT = (60, 40, 20)
CUL_BUTON = (100, 160, 100)
CUL_BUTON_HOVER = (120, 180, 120)
CUL_OVERLAY = (235, 230, 210)
CUL_HIGHLIGHT = (255, 50, 50)
IMG_LEMN = None


# Ne asiguram ca jucatorul nu da click in afara ferestrei sau peste o piesa deja pusa.
def mutare_valida(mat, i, j):
    if not (0 <= i < len(mat) and 0 <= j < len(mat[0])): return -1
    if mat[i][j] != 0: return -2
    return 0


# Functie care scaneaza tabla intr-o directie specifica (sus, jos, diagonala)
# ca sa numere cate piese consecutive de aceeasi culoare avem.
def numar_piese(mat, i, j, dir_i, dir_j, simb_juc):
    nr = 0
    ci = i + dir_i
    cj = j + dir_j
    while (0 <= ci < len(mat)) and (0 <= cj < len(mat[0])) and mat[ci][cj] == simb_juc:
        nr += 1
        ci += dir_i
        cj += dir_j
    return nr


# Un fel de filtru pentru AI care cauta un sablon de 4 piese specifice.
def analiza_axa_patru(mat, i, j, dir_i, dir_j, simbol):
    mat_slice = []
    for k in range(-4, 5):
        ci = i + (k * dir_i)
        cj = j + (k * dir_j)
        if 0 <= ci < len(mat) and 0 <= cj < len(mat):
            mat_slice.append(mat[ci][cj])
        else:
            mat_slice.append(-1)

    s = simbol
    tipare = [[s, s, s, s, 0], [0, s, s, s, s], [s, s, 0, s, s], [s, 0, s, s, s], [s, s, s, 0, s]]
    for start in range(5):
        fragment = mat_slice[start: start + 5]
        if fragment in tipare:
            if fragment[4 - start] == s: return True
    return False


# REGULA RENJU: "Double-Four" (Dublu 4)
# Negrul (cel care muta primul) primeste interdictie sa faca doua linii de 4 piese simultan.
# De ce? Pentru ca ar insemna o victorie garantata (Albul ar putea bloca doar o parte),
# iar Negrul ar fi prea greu de batut (Foul).
def verificare_double_four(mat, i, j, simbol):
    directii = [(1, 0), (0, 1), (1, 1), (1, -1)]
    cnt = 0
    for d in directii:
        if analiza_axa_patru(mat, i, j, d[0], d[1], simbol): cnt += 1
    return cnt >= 2


# Verificam daca avem un castigator dupa ultima mutare.
# REGULA RENJU: "Overline". Negrul (1) trebuie sa faca FIX 5 piese.
# Daca din greseala face o linie de 6 sau mai multe, el de fapt pierde meciul (isi da autogol).
# Albul (2) nu are restrictia asta, castiga oricum daca face minim 5.
def verificare_castigator(mat, i, j, simb_juc):
    directii = [((0, 1), (0, -1)), ((1, 0), (-1, 0)), ((1, 1), (-1, -1)), ((1, -1), (-1, 1))]
    for d1, d2 in directii:
        nr1 = numar_piese(mat, i, j, d1[0], d1[1], simb_juc)
        nr2 = numar_piese(mat, i, j, d2[0], d2[1], simb_juc)
        total = 1 + nr1 + nr2

        if simb_juc == 2 and total >= 5:
            return 1
        elif simb_juc == 1 and total == 5:
            return 1
        elif simb_juc == 1 and total > 5:
            return -1  # Autogol (overline) pentru negru

        if simb_juc == 1 and verificare_double_four(mat, i, j, simb_juc): return -2
    return 0


# Returneaza o lista cu toate spatiile goale de pe tabla (optiunile de mutare).
def gaseste_mutari_disponibile(mat):
    return [(i, j) for i in range(len(mat)) for j in range(len(mat)) if mat[i][j] == 0]


# Inteligenta artificiala face o mutare "in minte" ca sa vada daca iese cineva castigator, apoi sterge urma.
def simuleaza_mutare(mat, i, j, valoare):
    mat[i][j] = valoare
    rez = verificare_castigator(mat, i, j, valoare)
    mat[i][j] = 0
    return rez


# Inima sistemului de punctare pentru AI. Analizeaza o linie si ii da o nota.
# O linie de 4 cu un capat liber e aproape de victorie (10000 puncte),
# in timp ce o linie de 2 e abia la inceput (100 puncte).
def evalueaza_potential_linie(mat, i, j, d_i, d_j, simbol):
    consecutive = 1
    open_ends = 0
    ci, cj = i + d_i, j + d_j
    while 0 <= ci < len(mat) and 0 <= cj < len(mat) and mat[ci][cj] == simbol:
        consecutive += 1
        ci += d_i
        cj += d_j
    if 0 <= ci < len(mat) and 0 <= cj < len(mat) and mat[ci][cj] == 0: open_ends += 1

    ci, cj = i - d_i, j - d_j
    while 0 <= ci < len(mat) and 0 <= cj < len(mat) and mat[ci][cj] == simbol:
        consecutive += 1
        ci -= d_i
        cj -= d_j
    if 0 <= ci < len(mat) and 0 <= cj < len(mat) and mat[ci][cj] == 0: open_ends += 1

    if consecutive >= 5: return 100000
    if consecutive == 4: return 10000 if open_ends >= 1 else 5000
    if consecutive == 3: return 2000 if open_ends == 2 else 500
    if consecutive == 2 and open_ends == 2: return 100
    return 1


# Aici ajutam AI-ul sa decida daca sa schimbe culoarea in faza initiala de Swap2.
# Scor pozitiv inseamna ca Negrul a ocupat bine centrul (deci AI-ul va fura Negrul).
def evalueaza_balanta_swap(mat):
    scor = 0
    center = len(mat) // 2
    for r in range(len(mat)):
        for c in range(len(mat)):
            if mat[r][c] == 1:
                scor += (10 - abs(r - center) - abs(c - center))
            elif mat[r][c] == 2:
                scor -= (10 - abs(r - center) - abs(c - center))
    return scor


# Creierul principal al jocului la modul Player vs AI.
# Aici se decide cat de "destept" gandeste adversarul in functie de setare.
def mutare_ai_manager(mat, ai_simb, op_simb, dificultate):
    mutari = gaseste_mutari_disponibile(mat)
    if not mutari: return None

    # Nivelul 1: Cam haotic. Se asigura doar ca nu pierde imediat si ca muta legal.
    if dificultate == 1:
        for m in mutari:
            if simuleaza_mutare(mat, m[0], m[1], ai_simb) == 1: return m
        for m in mutari:
            if simuleaza_mutare(mat, m[0], m[1], op_simb) == 1: return m
        mutari_safe = [m for m in mutari if simuleaza_mutare(mat, m[0], m[1], ai_simb) not in [-1, -2]]
        return random.choice(mutari_safe) if mutari_safe else random.choice(mutari)

    # Nivelul 2: AI-ul trage spre centrul tablei si incearca sa prinda piesele in grupuri.
    if dificultate == 2:
        for m in mutari:
            if simuleaza_mutare(mat, m[0], m[1], ai_simb) == 1: return m
        for m in mutari:
            if simuleaza_mutare(mat, m[0], m[1], op_simb) == 1: return m

        mutari_valide = [m for m in mutari if simuleaza_mutare(mat, m[0], m[1], ai_simb) not in [-1, -2]]
        if not mutari_valide: return random.choice(mutari)

        best_move = random.choice(mutari_valide)
        best_score = -1000
        directii = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]
        center = len(mat) // 2

        for m in mutari_valide:
            scor = 0
            scor -= (abs(m[0] - center) + abs(m[1] - center)) * 0.5
            for d in directii:
                ni, nj = m[0] + d[0], m[1] + d[1]
                if 0 <= ni < len(mat) and 0 <= nj < len(mat):
                    if mat[ni][nj] == ai_simb:
                        scor += 2.0
                    elif mat[ni][nj] == op_simb:
                        scor += 1.5
            if scor > best_score:
                best_score = scor
                best_move = m
        return best_move

    # Nivelul 3: Terminator. Analizeaza heatmap-ul (vede ce scor obtine pe fiecare mutare posibila)
    # si se axeaza un pic mai mult pe aparare ca sa iti strice planurile (nota x 1.2 pe defensiva).
    if dificultate == 3:
        for m in mutari:
            if simuleaza_mutare(mat, m[0], m[1], ai_simb) == 1: return m
        for m in mutari:
            if simuleaza_mutare(mat, m[0], m[1], op_simb) == 1: return m

        mutari_valide = [m for m in mutari if simuleaza_mutare(mat, m[0], m[1], ai_simb) not in [-1, -2]]
        if not mutari_valide: return random.choice(mutari)

        candidati = []
        directii_unice = [(0, 1), (1, 0), (1, 1), (1, -1)]
        center = len(mat) // 2

        for m in mutari_valide:
            i, j = m
            scor_total = 0
            scor_total += (len(mat) - (abs(i - center) + abs(j - center)))

            for d in directii_unice:
                atk = evalueaza_potential_linie(mat, i, j, d[0], d[1], ai_simb)
                defe = evalueaza_potential_linie(mat, i, j, d[0], d[1], op_simb)
                scor_total += atk * 1.0
                scor_total += defe * 1.2
            candidati.append((scor_total, m))

        candidati.sort(key=lambda x: x[0], reverse=True)
        return candidati[0][1]

    return random.choice(mutari)


# ==========================================
#  INTERFATA GRAFICA (Aici dam viata codului)
# ==========================================

# Daca avem imaginea cu textura de lemn incarcata, o punem pe fundal, altfel desenam un crem simplu.
def deseneaza_fundal(screen):
    if IMG_LEMN:
        screen.blit(IMG_LEMN, (0, 0))
    else:
        screen.fill(CUL_FUNDAL)


# Generam butoane interactive, care isi schimba usor culoarea cand pui mouse-ul pe ele (hover).
def deseneaza_buton(screen, rect, text, font, mouse_pos):
    culoare = CUL_BUTON_HOVER if rect.collidepoint(mouse_pos) else CUL_BUTON
    pygame.draw.rect(screen, culoare, rect, border_radius=12)
    pygame.draw.rect(screen, CUL_NEGRU, rect, 2, border_radius=12)
    txt_surf = font.render(text, True, (255, 255, 255))
    text_rect = txt_surf.get_rect(center=rect.center)
    screen.blit(txt_surf, text_rect)


# Asta e primul ecran cand pornesti aplicatia. Te intreaba in ce mod vrei sa joci.
def deseneaza_meniu_principal(screen, font_title, font_btn, mouse_pos):
    deseneaza_fundal(screen)

    titlu = font_title.render("GOMOKU RENJU", True, CUL_NEGRU)
    screen.blit(titlu, (WIDTH // 2 - titlu.get_width() // 2, 100))

    btn_pvc = pygame.Rect(WIDTH // 2 - 125, HEIGHT // 2 - 40, 250, 60)
    btn_pvp = pygame.Rect(WIDTH // 2 - 125, HEIGHT // 2 + 40, 250, 60)

    deseneaza_buton(screen, btn_pvc, "1 Player (vs AI)", font_btn, mouse_pos)
    deseneaza_buton(screen, btn_pvp, "2 Players (PvP)", font_btn, mouse_pos)


# Daca joci cu AI-ul, trebuie sa te hotarasti cat de tare vrei sa te bata.
def deseneaza_meniu_dificultate(screen, font_title, font_btn, mouse_pos):
    deseneaza_fundal(screen)
    titlu = font_title.render("ALEGE DIFICULTATEA", True, CUL_NEGRU)
    screen.blit(titlu, (WIDTH // 2 - titlu.get_width() // 2, 80))

    btn_usor = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 90, 200, 50)
    btn_mediu = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 20, 200, 50)
    btn_greu = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 50, 200, 50)

    deseneaza_buton(screen, btn_usor, "USOR", font_btn, mouse_pos)
    deseneaza_buton(screen, btn_mediu, "MEDIU", font_btn, mouse_pos)
    deseneaza_buton(screen, btn_greu, "GREU", font_btn, mouse_pos)


# Meniul special de decizie (Swap2). Al doilea jucator/AI-ul se uita la primele 3 mutari
# puse pe tabla si zice: "Hmm, Negrul pare in avantaj, iau eu Negrul" sau "Sunt ok cu Albul".
def deseneaza_meniu_swap(screen, font_title, font_btn, mouse_pos):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    titlu = font_title.render("DECIDE ROLUL (SWAP2)", True, (255, 255, 255))
    screen.blit(titlu, (WIDTH // 2 - titlu.get_width() // 2, 150))

    btn_alb = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 60, 300, 50)
    btn_swap = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 + 20, 300, 50)

    deseneaza_buton(screen, btn_alb, "Joaca cu ALB (Ramai)", font_btn, mouse_pos)
    deseneaza_buton(screen, btn_swap, "SCHIMBA (Joaca cu NEGRU)", font_btn, mouse_pos)


# Aici construim reteaua de linii si punem pe ele piesele jucatorilor.
# Am adaugat si un contur fin (highlight) pe ultima piesa pusa ca sa stii unde s-a mutat.
def deseneaza_grid(screen, font, tabla, last_move):
    for i in range(N + 1):
        pos = MARGINE + i * DIM
        pygame.draw.line(screen, CUL_GRID, (MARGINE, pos), (WIDTH - MARGINE, pos), 2)
        pygame.draw.line(screen, CUL_GRID, (pos, MARGINE), (pos, HEIGHT - MARGINE), 2)

    for i in range(N):
        txt_col = font.render(chr(65 + i), True, CUL_TEXT)
        screen.blit(txt_col, (MARGINE + i * DIM + DIM // 2 - txt_col.get_width() // 2, MARGINE - 20))
        txt_row = font.render(str(i + 1), True, CUL_TEXT)
        screen.blit(txt_row, (MARGINE - 25, MARGINE + i * DIM + DIM // 2 - txt_row.get_height() // 2))

    for r in range(N):
        for c in range(N):
            if tabla[r][c] != 0:
                cx = MARGINE + c * DIM + DIM // 2
                cy = MARGINE + r * DIM + DIM // 2
                culoare = CUL_NEGRU if tabla[r][c] == 1 else CUL_ALB

                # Punem putina "umbra" ca sa para piesele mai de calitate, stil 3D.
                pygame.draw.circle(screen, (100, 100, 100), (cx + 2, cy + 2), DIM // 2 - 5)
                pygame.draw.circle(screen, culoare, (cx, cy), DIM // 2 - 5)

                if last_move == (r, c):
                    pygame.draw.circle(screen, CUL_HIGHLIGHT, (cx, cy), 4)


# Fereastra care apare cand meciul s-a terminat.
def deseneaza_game_over(screen, text, font_big, font_small):
    t_surf = font_big.render(text, True, (200, 0, 0))
    s_surf = font_small.render("Click oriunde pt Meniu Principal", True, (50, 50, 50))

    cx, cy = WIDTH // 2, HEIGHT // 2
    w = t_surf.get_width() + 60
    h = 100
    rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)

    pygame.draw.rect(screen, CUL_OVERLAY, rect)
    pygame.draw.rect(screen, CUL_GRID, rect, 3)
    screen.blit(t_surf, (cx - t_surf.get_width() // 2, cy - 25))
    screen.blit(s_surf, (cx - s_surf.get_width() // 2, cy + 25))


# Un mic text jos care te ghideaza cand esti in faza ciudata de plasare la Swap2.
def deseneaza_info_faza(screen, font, faza, piese):
    if faza == "SWAP2_PLASARE":
        txt = font.render(f"Faza SWAP2: Plaseaza primele 3 piese ({piese}/3)", True, (0, 0, 150))
        screen.blit(txt, (20, HEIGHT - 30))
    elif faza == "JOC_NORMAL":
        pass


# ==========================================
#  MOTORUL PRINCIPAL (Unde totul se leaga)
# ==========================================

def start_joc():
    global IMG_LEMN
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Gomoku - Proiect Final")
    clock = pygame.time.Clock()

    # Incarcam poza de fundal daca o avem in acelasi folder cu scriptul, altfel ignoram.
    try:
        folder_curent = os.path.dirname(os.path.abspath(__file__))
        cale_jpg = os.path.join(folder_curent, "lemn.jpg")
        if os.path.exists(cale_jpg):
            raw = pygame.image.load(cale_jpg)
            IMG_LEMN = pygame.transform.scale(raw, (WIDTH, HEIGHT))
    except:
        pass

    # Pregatim seturile de texte
    FONT_TITLE = pygame.font.SysFont('Arial', 50, bold=True)
    FONT_BTN = pygame.font.SysFont('Arial', 24, bold=True)
    FONT_IDX = pygame.font.SysFont('Arial', 14, bold=True)
    FONT_MSG = pygame.font.SysFont('Arial', 32, bold=True)
    FONT_SMALL = pygame.font.SysFont('Arial', 16)

    stare_curenta = "MENIU"
    faza_joc = "NORMAL"  # Poate fi NORMAL, SWAP2_PLASARE, SWAP2_DECIZIE
    piese_swap = 0

    mod_joc = 0
    dificultate = 2

    # Setari implicite de inceput: Tu joci cu Negru (1), AI cu Alb (2)
    ai_simbol = 2
    uman_simbol = 1

    tabla = []
    tura = 1
    game_over = False
    mesaj_final = ""
    last_move = None
    running = True

    # Aici incepe bucla principala, tine programul deschis cat timp jucam.
    while running:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():

            # Ne asiguram ca butonul rosu [X] inchide jocul corect
            if event.type == pygame.QUIT: running = False

            # --- GESTIONAM MENIUL PRINCIPAL ---
            if stare_curenta == "MENIU":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    btn_pvc = pygame.Rect(WIDTH // 2 - 125, HEIGHT // 2 - 40, 250, 60)
                    btn_pvp = pygame.Rect(WIDTH // 2 - 125, HEIGHT // 2 + 40, 250, 60)
                    if btn_pvc.collidepoint(mouse_pos):
                        mod_joc = 1
                        stare_curenta = "SELECT_DIFICULTATE"
                    elif btn_pvp.collidepoint(mouse_pos):
                        mod_joc = 2
                        stare_curenta = "JOC"
                        # Resetam tabla complet pentru un meci nou
                        tabla = [[0] * N for _ in range(N)]
                        tura = 1
                        game_over = False
                        last_move = None
                        faza_joc = "SWAP2_PLASARE"
                        piese_swap = 0

            # --- GESTIONAM MENIUL DE DIFICULTATE ---
            elif stare_curenta == "SELECT_DIFICULTATE":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    btn_usor = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 90, 200, 50)
                    btn_mediu = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 20, 200, 50)
                    btn_greu = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 50, 200, 50)
                    if btn_usor.collidepoint(mouse_pos):
                        dificultate = 1;
                        stare_curenta = "JOC"
                    elif btn_mediu.collidepoint(mouse_pos):
                        dificultate = 2;
                        stare_curenta = "JOC"
                    elif btn_greu.collidepoint(mouse_pos):
                        dificultate = 3;
                        stare_curenta = "JOC"

                    # Resetam totul pentru a intra direct in bataie cu AI-ul
                    if stare_curenta == "JOC":
                        tabla = [[0] * N for _ in range(N)]
                        tura = 1
                        game_over = False
                        last_move = None
                        ai_simbol = 2
                        uman_simbol = 1
                        faza_joc = "SWAP2_PLASARE"
                        piese_swap = 0

            # --- GESTIONAM DECIZIA DE SCHIMBARE CULOARE IN PvP ---
            elif stare_curenta == "JOC" and faza_joc == "SWAP2_DECIZIE" and mod_joc == 2:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    btn_alb = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 60, 300, 50)
                    btn_swap = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 + 20, 300, 50)

                    if btn_alb.collidepoint(mouse_pos):
                        faza_joc = "JOC_NORMAL"
                        tura = 2  # Urmeaza Albul
                    elif btn_swap.collidepoint(mouse_pos):
                        faza_joc = "JOC_NORMAL"
                        tura = 2  # Tehnic, jucatorii fac schimb de scaune, dar e randul albului oricum

            # --- GESTIONAM CLICK-URILE PE TABLA ---
            elif stare_curenta == "JOC":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

                    # Daca meciul s-a terminat, te intoarce in meniu ca sa te racoresti
                    if game_over: stare_curenta = "MENIU"; continue

                    # Daca asteptam dupa AI, ingnoram click-urile utilizatorului nerabdator
                    if mod_joc == 1 and tura == ai_simbol and faza_joc != "SWAP2_PLASARE":
                        continue

                    # Transformam click-ul brut in pixeli in niste coordonate precise (r, c)
                    mx, my = event.pos
                    c = (mx - MARGINE) // DIM
                    r = (my - MARGINE) // DIM
                    if 0 <= r < N and 0 <= c < N and tabla[r][c] == 0:

                        # REGULA SWAP2: Plasarea celor 3 piese initiale de catre primul jucator.
                        if faza_joc == "SWAP2_PLASARE":
                            tabla[r][c] = tura
                            last_move = (r, c)
                            piese_swap += 1
                            tura = 1 if piese_swap % 2 == 0 else 2

                            if piese_swap == 3:
                                faza_joc = "SWAP2_DECIZIE"

                        # Aici decurge jocul standard, muti, verificam castigatorul, dam tura mai departe.
                        elif faza_joc == "JOC_NORMAL":
                            tabla[r][c] = tura
                            last_move = (r, c)
                            rez = verificare_castigator(tabla, r, c, tura)
                            if rez != 0:
                                game_over = True
                                nume = "NEGRU" if tura == 1 else "ALB"
                                if rez == 1:
                                    mesaj_final = f"VICTORIE: {nume}!"
                                else:
                                    mesaj_final = "VICTORIE: ALB (Foul X)"
                            tura = 3 - tura

        # ==========================================
        # DESENAM EFECTIV LUCRURILE PE ECRAN
        # ==========================================

        if stare_curenta == "MENIU":
            deseneaza_meniu_principal(screen, FONT_TITLE, FONT_BTN, mouse_pos)

        elif stare_curenta == "SELECT_DIFICULTATE":
            deseneaza_meniu_dificultate(screen, FONT_TITLE, FONT_BTN, mouse_pos)

        elif stare_curenta == "JOC":
            deseneaza_fundal(screen)
            deseneaza_grid(screen, FONT_IDX, tabla, last_move)
            deseneaza_info_faza(screen, FONT_SMALL, faza_joc, piese_swap)

            # AI-ul sta putin pe ganduri si alege daca ia Negrul sau isi pastreaza Albul
            if faza_joc == "SWAP2_DECIZIE":
                if mod_joc == 1:
                    pygame.display.flip()
                    pygame.time.wait(500)

                    balanta = evalueaza_balanta_swap(tabla)

                    if balanta > 3:
                        ai_simbol = 1
                        uman_simbol = 2
                        print("AI a ales: SCHIMB (Joaca cu Negru)")
                    else:
                        ai_simbol = 2
                        uman_simbol = 1
                        print("AI a ales: ALB (Ramane asa)")

                    faza_joc = "JOC_NORMAL"
                    tura = 2

                else:  # Daca e PvP, dam jucatorilor buton de decizie
                    deseneaza_meniu_swap(screen, FONT_TITLE, FONT_BTN, mouse_pos)

            # Cand vine randul AI-ului in jocul normal, apelam logica si asteptam mutarea lui
            elif faza_joc == "JOC_NORMAL" and mod_joc == 1 and tura == ai_simbol and not game_over:
                pygame.display.flip()
                m_ai = mutare_ai_manager(tabla, ai_simbol, uman_simbol, dificultate)

                if m_ai:
                    r, c = m_ai
                    tabla[r][c] = ai_simbol
                    last_move = (r, c)
                    rez = verificare_castigator(tabla, r, c, ai_simbol)
                    if rez != 0:
                        game_over = True
                        mesaj_final = "VICTORIE: AI!"
                    tura = uman_simbol
                else:
                    game_over = True
                    mesaj_final = "REMIZA!"

            if game_over: deseneaza_game_over(screen, mesaj_final, FONT_MSG, FONT_SMALL)

        # Actualizam tot ce s-a schimbat pe fereastra, setand 60 FPS sa se miste curat
        pygame.display.flip()
        clock.tick(60)

    # In caz ca am iesit, inchidem procesele curat si oprim programul.
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    start_joc()