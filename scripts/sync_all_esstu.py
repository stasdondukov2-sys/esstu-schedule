import ssl
import time
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

ESSTU_BASE_URL = "https://portal.esstu.ru"
DEMO_DIR = Path(__file__).resolve().parents[1] / "demo_data"

SECTIONS = ["bakalavriat", "spezialitet", "zo1", "zo2"]
TEACHER_SECTIONS = ["bakalavriat", "spezialitet"]

# Полная сетка групп по курсам (1..6) и факультетам ВСГУТУ
BAK_COURSES = {
    1: [
        ("1", "1146 тпуп"), ("2", "1136 тилп"), ("3", "1126 бт"), ("4", "246 эн.рес.сб"),
        ("5", "316 ээ"), ("6", "326 тэс"), ("7", "336 эасу"), ("8", "416 тм"), ("9", "426 ат"),
        ("10", "516 пгс"), ("11", "526 тгв"), ("12", "616 эк"), ("13", "636 юр"),
        ("14", "Б716 ивт"), ("15", "Б736 при"), ("16", "Б746 иб"), ("17", "Б766 пи"),
    ],
    2: [
        ("41", "245 эн.рес.сб"), ("42", "1145 тпуп"), ("43", "1135 тилп"), ("44", "315 ээ"),
        ("45", "325 тэс"), ("46", "415 тм"), ("47", "425 ат"), ("48", "515 пгс"),
        ("49", "615 эк"), ("50", "635 юр"), ("51", "Б715 ивт"), ("52", "Б735 при"),
        ("53", "Б745 иб"), ("54", "Б765 пи"),
    ],
    3: [
        ("91", "244 эн/р сб."), ("92", "1144 тпуп"), ("93", "1134 тилп"), ("94", "314 ээ"),
        ("95", "324 тэс"), ("96", "414 тм"), ("97", "514 пгс"), ("98", "614 эк"),
        ("99", "634 юр"), ("100", "Б714 ивт"), ("101", "Б734 при"), ("102", "Б744 иб"), ("103", "Б764 пи"),
    ],
    4: [
        ("150", "1143 тпуп"), ("151", "1133 тилп"), ("152", "243 эн.рес.сб"), ("153", "313 ээ"),
        ("154", "323 тэс"), ("155", "413 тм"), ("156", "513 пгс"), ("157", "613 эк"),
        ("158", "633 юр"), ("159", "Б713 ивт"), ("160", "Б733 при"), ("161", "Б762 пи"), ("162", "Б763 пи"),
    ],
    5: [
        ("208", "252 гор.дело"), ("209", "462 св"), ("210", "452 сдм"),
        ("211", "552 сузс"), ("212", "652 эб"), ("213", "742 ибс"),
    ],
    6: [
        ("240", "251 гор.дело"), ("241", "461 св"), ("242", "551 сузс"),
    ],
}

SPEZ_COURSES = {
    1: [
        ("301", "М516 ээ (Маг.)"), ("302", "М766 пи (Маг.)"), ("303", "М1146 тпуп (Маг.)"),
        ("304", "М526 пгс (Маг.)"), ("305", "К196 тм (Колледж)"), ("306", "К316 ээ (Колледж)"),
        ("307", "К766 исп (Колледж)"), ("308", "К616 эк (Колледж)"),
    ],
    2: [
        ("321", "М514 ээ (Маг.)"), ("322", "М764 пи (Маг.)"), ("323", "М1144 тпуп (Маг.)"),
        ("324", "К195 тм (Колледж)"), ("325", "К765 исп (Колледж)"), ("326", "К635 юр (Колледж)"),
    ],
    3: [
        ("341", "К194 тм (Колледж)"), ("342", "К764 исп (Колледж)"), ("343", "К314 ээ (Колледж)"),
    ],
}

ZO1_COURSES = {
    1: [("401", "ЗБ-1146 тпуп"), ("402", "ЗБ-316 ээ"), ("403", "ЗБ-516 пгс"), ("404", "ЗБ-766 пи")],
    2: [("411", "ЗБ-1145 тпуп"), ("412", "ЗБ-315 ээ"), ("413", "ЗБ-515 пгс"), ("414", "ЗБ-765 пи")],
    3: [("421", "ЗБ-1144 тпуп"), ("422", "ЗБ-314 ээ"), ("423", "ЗБ-514 пгс"), ("424", "ЗБ-764 пи")],
    4: [("431", "ЗБ-1143 тпуп"), ("432", "ЗБ-313 ээ"), ("433", "ЗБ-762 пи")],
    5: [("441", "ЗБ-252 гор.дело"), ("442", "ЗБ-462 св")],
}

ZO2_COURSES = {
    1: [("501", "ЗБ-616 эк"), ("502", "ЗБ-636 юр"), ("503", "ЗМ-616 мен (Маг.)")],
    2: [("511", "ЗБ-615 эк"), ("512", "ЗБ-635 юр"), ("513", "ЗМ-635 юр (Маг.)")],
    3: [("521", "ЗБ-614 эк"), ("522", "ЗБ-634 юр")],
    4: [("531", "ЗБ-613 эк"), ("532", "ЗБ-633 юр")],
}


def build_raspisan_table_html(courses_dict):
    max_rows = max(len(v) for v in courses_dict.values())
    header_tds = "".join(
        f'  <TD WIDTH="17%" VALIGN="TOP"><FONT FACE="Times New Roman" SIZE=5 COLOR="#ff00ff"><P ALIGN="CENTER"> {c} курс </FONT></TD>\n'
        for c in range(1, 7)
    )
    body_trs = []
    for r in range(max_rows):
        tds = []
        for c in range(1, 7):
            items = courses_dict.get(c, [])
            if r < len(items):
                gid, gname = items[r]
                tds.append(f'  <TD><P ALIGN="CENTER"><A HREF="{gid}.htm"><FONT FACE="Times New Roman">{gname}</FONT></A></TD>')
            else:
                tds.append('  <TD><P ALIGN="CENTER"></TD>')
        body_trs.append("<TR>\n" + "\n".join(tds) + "\n</TR>")

    return f"""<HTML>
<HEAD><META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=windows-1251"><TITLE>raspisan</TITLE></HEAD>
<BODY LINK="#0000ff" VLINK="#800080">
<FONT FACE="Times New Roman" SIZE=6 COLOR="#0000ff"><P>Расписание занятий студентов</P></FONT>
<TABLE BORDER CELLSPACING=1 CELLPADDING=3 WIDTH=623>
<TR>\n{header_tds}</TR>
{chr(10).join(body_trs)}
</TABLE>
</BODY></HTML>"""


def build_group_schedule_html(gid, gname, is_zo=False):
    name_low = gname.lower()
    if is_zo:
        return f"""<HTML>
<HEAD><META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=windows-1251"><TITLE>{gid}</TITLE></HEAD>
<BODY>
<FONT FACE="Times New Roman" SIZE=5 COLOR="#0000ff"><P>Расписание экзаменационной сессии заочной группы:</FONT>
<FONT FACE="Times New Roman" SIZE=6 COLOR="#ff00ff"> {gname}</P></FONT>
<TABLE BORDER CELLSPACING=3 BORDERCOLOR="#000000" CELLPADDING=2 WIDTH=801>
<TR><TD>Пары</TD><TD>1-я</TD><TD>2-я</TD><TD>3-я</TD><TD>4-я</TD><TD>5-я</TD><TD>6-я</TD><TD>7-я</TD></TR>
<TR><TD>Время</TD><TD>09:00-10:35</TD><TD>10:45-12:20</TD><TD>13:00-14:35</TD><TD>14:45-16:20</TD><TD>16:25-18:00</TD><TD>18:05-19:40</TD><TD>19:45-21:20</TD></TR>
<TR><TD>15 янв</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>лек.Высшая математика ЦЫРЕНОВА В.Б. а.8305</TD><TD>пр.Высшая математика ЦЫРЕНОВА В.Б. а.8204</TD><TD>конс.Высшая математика ЦЫРЕНОВА В.Б. а.8204</TD></TR>
<TR><TD>16 янв</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>лек.Информатика ДОРЖИЕВ Б.Ц. а.0110</TD><TD>лаб.Информатика (1 п/г) ДОРЖИЕВ Б.Ц. а.0114 лаб.Информатика (2 п/г) АЮШЕЕВ Т.В. а.0116</TD><TD>_</TD></TR>
<TR><TD>17 янв</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>лек.Физика ДАРИБАЗАРОН Э.Ч.ФИЗ. а.0410 и/д</TD><TD>лаб.Физика ВАГАНОВА В.И. а.0415</TD><TD>зач.Физика ДАРИБАЗАРОН Э.Ч.ФИЗ. а.0410 и/д</TD></TR>
<TR><TD>18 янв</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>лек.История России СОКОЛОВ С.М. а.0302</TD><TD>пр.История России СОКОЛОВ С.М. а.8100а</TD><TD>зач.История России СОКОЛОВ С.М. а.8100а</TD></TR>
<TR><TD>19 янв</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>лек.Автоматизированные системы НАЙДАНОВ Ч.А. а.3105</TD><TD>пр.Автоматизированные системы НАЙДАНОВ Ч.А. а.3105</TD><TD>_</TD></TR>
<TR><TD>20 янв</TD><TD>экз.Высшая математика ЦЫРЕНОВА В.Б. а.8305</TD><TD>экз.Информатика ДОРЖИЕВ Б.Ц. а.0110</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD></TR>
<TR><TD><FONT COLOR="#0000ff">22 янв</FONT></TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD><FONT COLOR="#0000ff">лек.Теоретические основы электротехники БАИРОВ А.М. а.3204</FONT></TD><TD><FONT COLOR="#0000ff">лаб.Теоретические основы электротехники БАИРОВ А.М. а.3208</FONT></TD><TD>_</TD></TR>
<TR><TD><FONT COLOR="#0000ff">23 янв</FONT></TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD><FONT COLOR="#0000ff">лек.Инженерная графика АЮШЕЕВ Т.В. а.8402</FONT></TD><TD><FONT COLOR="#0000ff">пр.Инженерная графика АЮШЕЕВ Т.В. а.8402</FONT></TD><TD>_</TD></TR>
<TR><TD><FONT COLOR="#0000ff">24 янв</FONT></TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD><FONT COLOR="#0000ff">лаб.Иностранный язык (англ.) ИВАНОВА А.В. а.15-504 лаб.Иностранный язык (франц.) ПУШКАРЕВА Ю.Г. а.15-572</FONT></TD><TD><FONT COLOR="#0000ff">зач.Иностранный язык ИВАНОВА А.В. а.15-504</FONT></TD><TD>_</TD></TR>
<TR><TD><FONT COLOR="#0000ff">25 янв</FONT></TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD><FONT COLOR="#0000ff">лек.Неорганическая химия БАЗАРОВА Ж.Г. а.0215</FONT></TD><TD><FONT COLOR="#0000ff">лаб.Неорганическая химия БАЗАРОВА Ж.Г. а.0218</FONT></TD><TD>_</TD></TR>
<TR><TD><FONT COLOR="#0000ff">26 янв</FONT></TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD><FONT COLOR="#0000ff">конс.Теоретические основы электротехники БАИРОВ А.М. а.3204</FONT></TD><TD>_</TD><TD>_</TD></TR>
<TR><TD><FONT COLOR="#0000ff">27 янв</FONT></TD><TD><FONT COLOR="#0000ff">экз.Теоретические основы электротехники БАИРОВ А.М. а.3204</FONT></TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD></TR>
</TABLE></BODY></HTML>"""

    if any(k in name_low for k in ("б7", "к7", "м7", "пи", "ивт", "при", "иб", "исп")):
        p_mon2 = "лек.Программная инженерия и ИИ ДОРЖИЕВ Б.Ц. а.0110"
        p_mon3 = "лаб.Технологии программирования (1 п/г) ДОРЖИЕВ Б.Ц. а.0114 лаб.Технологии программирования (2 п/г) ЧИМИТОВ Д.Н. а.8412"
        p_wed1 = "лек.Базы данных и экспертные системы ЧИМИТОВ Д.Н. а.8410"
        p_wed2 = "лаб.Базы данных (1 п/г) ЧИМИТОВ Д.Н. а.8412 лаб.Компьютерная графика (2 п/г) АЮШЕЕВ Т.В. а.8402"
    elif any(k in name_low for k in ("эн", "ээ", "тэс", "эасу", "м51")):
        p_mon2 = "лек.Теоретические основы электротехники БАИРОВ А.М. а.3204"
        p_mon3 = "лаб.Электрические сети (1 п/г) БАИРОВ А.М. а.3208 лаб.Теплоэнергетика (2 п/г) ДАМДИНОВ Б.Б. а.3310"
        p_wed1 = "лек.Физика ДАРИБАЗАРОН Э.Ч.ФИЗ. а.0410 и/д"
        p_wed2 = "лаб.Физика (1 п/г) ВАГАНОВА В.И. а.0415 пр.Физика (2 п/г) ЖИГЖИТОВА С.Б. а.0422"
    else:
        p_mon2 = "лек.Физика 1 ДАРИБАЗАРОН Э.Ч.ФИЗ. а.0410 и/д"
        p_mon3 = "пр.Физика 1 ЖИГЖИТОВА С.Б. а.0422"
        p_wed1 = "лек.Неорганическая химия БАЗАРОВА Ж.Г. а.0215"
        p_wed2 = "лаб.Неорганическая химия (1 п/г) БАЗАРОВА Ж.Г. а.0218 лаб.Физика 1 (2 п/г) ВАГАНОВА В.И. а.0415"

    return f"""<HTML>
<HEAD><META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=windows-1251"><TITLE>{gid}</TITLE></HEAD>
<BODY>
<FONT FACE="Times New Roman" SIZE=5 COLOR="#0000ff"><P>Расписание занятий учебной группы:</FONT>
<FONT FACE="Times New Roman" SIZE=6 COLOR="#ff00ff"> {gname}</P></FONT>
<TABLE BORDER CELLSPACING=3 BORDERCOLOR="#000000" CELLPADDING=2 WIDTH=801>
<TR><TD>Пары</TD><TD>1-я</TD><TD>2-я</TD><TD>3-я</TD><TD>4-я</TD><TD>5-я</TD><TD>6-я</TD></TR>
<TR><TD>Время</TD><TD>09:00-10:35</TD><TD>10:45-12:20</TD><TD>13:00-14:35</TD><TD>14:45-16:20</TD><TD>16:25-18:00</TD><TD>18:05-19:40</TD></TR>
<TR><TD>Пнд</TD><TD>лаб.Иностранный язык (франц.) ПУШКАРЕВА Ю.Г. а.15-572 лаб.Иностранный язык (нем.) ХАМАГАНОВА В.М. а.15-568 лаб.Иностранный язык (англ. 1 п/г) ИВАНОВА А.В. а.15-504 лаб.Иностранный язык (англ. 2 п/г) СМИРНОВА Е.К. а.15-506</TD><TD>{p_mon2}</TD><TD>{p_mon3}</TD><TD>Физическая культура и спорт ФКС 1 а.9-Спорт1</TD><TD>_</TD><TD>_</TD></TR>
<TR><TD>Втр</TD><TD>_</TD><TD>лек.Высшая математика ЦЫРЕНОВА В.Б. а.8305</TD><TD>пр.Высшая математика ЦЫРЕНОВА В.Б. а.8204</TD><TD>лаб.Информатика (1 п/г) ДОРЖИЕВ Б.Ц. а.0114 лаб.Информатика (2 п/г) АЮШЕЕВ Т.В. а.0116</TD><TD>_</TD><TD>_</TD></TR>
<TR><TD>Срд</TD><TD>{p_wed1}</TD><TD>{p_wed2}</TD><TD>пр.Инженерная графика АЮШЕЕВ Т.В. а.8402</TD><TD>_</TD><TD>_</TD><TD>_</TD></TR>
<TR><TD>Чтв</TD><TD>лек.Информатика ДОРЖИЕВ Б.Ц. а.0110</TD><TD>лаб.Информатика (1 п/г) ДОРЖИЕВ Б.Ц. а.0114 лаб.Информатика (2 п/г) АЮШЕЕВ Т.В. а.0116</TD><TD>Физическая культура и спорт ФКС 1 а.9-Спорт1</TD><TD>_</TD><TD>_</TD><TD>_</TD></TR>
<TR><TD>Птн</TD><TD>_</TD><TD>лек.История России СОКОЛОВ С.М. а.0302</TD><TD>пр.История России СОКОЛОВ С.М. а.8100а</TD><TD>_</TD><TD>_</TD><TD>_</TD></TR>
<TR><TD>Сбт</TD><TD>лек.Автоматизированные системы управления НАЙДАНОВ Ч.А. а.3105</TD><TD>пр.Автоматизированные системы управления НАЙДАНОВ Ч.А. а.3105</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD></TR>
<TR><TD><FONT COLOR="#0000ff">Пнд</FONT></TD><TD><FONT COLOR="#0000ff">лаб.Иностранный язык (франц.) ПУШКАРЕВА Ю.Г. а.15-572 лаб.Иностранный язык (нем.) ХАМАГАНОВА В.М. а.15-568 лаб.Иностранный язык (англ. 1 п/г) ИВАНОВА А.В. а.15-504 лаб.Иностранный язык (англ. 2 п/г) СМИРНОВА Е.К. а.15-506</FONT></TD><TD><FONT COLOR="#0000ff">лек.История России СОКОЛОВ С.М. а.0302</FONT></TD><TD><FONT COLOR="#0000ff">пр.История России СОКОЛОВ С.М. а.8100а</FONT></TD><TD><FONT COLOR="#0000ff">Физическая культура и спорт ФКС 1 а.9-Спорт1</FONT></TD><TD>_</TD><TD>_</TD></TR>
<TR><TD><FONT COLOR="#0000ff">Втр</FONT></TD><TD>_</TD><TD><FONT COLOR="#0000ff">лек.Высшая математика ЦЫРЕНОВА В.Б. а.8305</FONT></TD><TD><FONT COLOR="#0000ff">пр.Высшая математика ЦЫРЕНОВА В.Б. а.8204</FONT></TD><TD>_</TD><TD>_</TD><TD>_</TD></TR>
<TR><TD><FONT COLOR="#0000ff">Срд</FONT></TD><TD><FONT COLOR="#0000ff">{p_wed1}</FONT></TD><TD><FONT COLOR="#0000ff">{p_wed2}</FONT></TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD></TR>
<TR><TD><FONT COLOR="#0000ff">Чтв</FONT></TD><TD><FONT COLOR="#0000ff">лек.Информатика ДОРЖИЕВ Б.Ц. а.0110</FONT></TD><TD><FONT COLOR="#0000ff">лаб.Информатика (1 п/г) ДОРЖИЕВ Б.Ц. а.0114 лаб.Информатика (2 п/г) АЮШЕЕВ Т.В. а.0116</FONT></TD><TD><FONT COLOR="#0000ff">Физическая культура и спорт ФКС 1 а.9-Спорт1</FONT></TD><TD>_</TD><TD>_</TD><TD>_</TD></TR>
<TR><TD><FONT COLOR="#0000ff">Птн</FONT></TD><TD>_</TD><TD><FONT COLOR="#0000ff">{p_mon2}</FONT></TD><TD><FONT COLOR="#0000ff">{p_mon3}</FONT></TD><TD>_</TD><TD>_</TD><TD>_</TD></TR>
<TR><TD><FONT COLOR="#0000ff">Сбт</FONT></TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD><TD>_</TD></TR>
</TABLE></BODY></HTML>"""


def seed_offline_groups():
    sections_map = [
        ("bakalavriat", BAK_COURSES, False),
        ("spezialitet", SPEZ_COURSES, False),
        ("zo1", ZO1_COURSES, True),
        ("zo2", ZO2_COURSES, True),
    ]
    count = 0
    for sec_name, c_dict, is_zo in sections_map:
        sec_dir = DEMO_DIR / sec_name
        sec_dir.mkdir(parents=True, exist_ok=True)
        (sec_dir / "raspisan.htm").write_bytes(build_raspisan_table_html(c_dict).encode("cp1251"))
        for _, g_list in c_dict.items():
            for gid, gname in g_list:
                html_g = build_group_schedule_html(gid, gname, is_zo=is_zo)
                (sec_dir / f"{gid}.htm").write_bytes(html_g.encode("cp1251"))
                count += 1
    print(f"📦 Локальная база предзаполнена: {count} групп во всех 4 разделах!")


def create_ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
        ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT")
    return ctx


SSL_CTX = create_ssl_ctx()


def download_raw(rel_path: str) -> bytes:
    url = f"{ESSTU_BASE_URL}/{rel_path.lstrip('/')}"
    req = urllib.request.Request(url, headers={"User-Agent": "ESSTU-Schedule-Sync/2.1"})
    with urllib.request.urlopen(req, timeout=8, context=SSL_CTX) as resp:
        return resp.read()


def sync_all_from_portal():
    seed_offline_groups()
    print("🌐 Пробуем синхронизировать живые таблицы напрямую с https://portal.esstu.ru ...")
    total_groups = 0
    for sec in SECTIONS:
        sec_dir = DEMO_DIR / sec
        try:
            raw_index = download_raw(f"{sec}/raspisan.htm")
            (sec_dir / "raspisan.htm").write_bytes(raw_index)
            soup = BeautifulSoup(raw_index.decode("cp1251", errors="replace"), "lxml")
            hrefs = {
                (a.get("href") or "").strip()
                for a in soup.find_all("a")
                if (a.get("href") or "").strip().endswith(".htm") and (a.get_text() or "").strip()
            }
            print(f"📂 Раздел [{sec}]: скачиваем {len(hrefs)} групп с портала...")
            for href in sorted(hrefs):
                try:
                    (sec_dir / href).write_bytes(download_raw(f"{sec}/{href}"))
                    total_groups += 1
                except Exception:
                    logging.getLogger(__name__).exception('Source synchronization failed: %s/%s', sec, href)
                time.sleep(0.03)
        except Exception as e:
            print(f"ℹ️ Раздел [{sec}] работает из локальной базы ({e})")

    if total_groups > 0:
        print(f"✅ С портала ВСГУТУ успешно обновлено групп: {total_groups}")


if __name__ == "__main__":
    sync_all_from_portal()
