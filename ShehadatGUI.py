
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Spacer
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
import pandas as pd
import arabic_reshaper
from bidi.algorithm import get_display
from PyPDF2 import PdfMerger
import os, sys, io
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import threading

# ==========================
#      ORIGINAL SCRIPT 
# ==========================

# Changeable variables
output_dir      =   ".\\Shehadat"                          
single_pdf_out  =   ".\\single"                       

space_between_tables = 15
row_heights = 22
Header_font_size=   11        
body_font_size  =   13        

os.makedirs(single_pdf_out, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

# Clean single folder if not empty
if os.listdir(single_pdf_out):
    print(f"Clearing old files from {single_pdf_out} ...")
    for f in os.listdir(single_pdf_out):
        file_path_to_remove = os.path.join(single_pdf_out, f)
        try:
            if os.path.isfile(file_path_to_remove):
                os.remove(file_path_to_remove)
        except Exception as e:
            print(f"Could not remove {file_path_to_remove}: {e}")

pdfmetrics.registerFont(TTFont('ArabicFont', 'times.ttf'))
margin = 15  
width, height = landscape(A4)

total_mark = 0
total_student = 0
student_name = ""
student_id = 0
students_data = []

def process_arabic_text(text):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def split_line_into_two_parts(header):
    words = header.split(' ')  
    if len(words) > 1:  
        midpoint = len(words) // 2  
        first_half = ' '.join(words[:midpoint])
        second_half = ' '.join(words[midpoint:])
        return '\n'.join([first_half, second_half])
    else:
        return header

def split_line_into_three_parts(header):
    words = header.split('_')  
    if len(words) > 1:  
        part1_end = len(words) // 3
        part2_end = 2 * (len(words) // 3)
        part1 = ' '.join(words[:part1_end])
        part2 = ' '.join(words[part1_end:part2_end])
        part3 = ' '.join(words[part2_end:])
        return '\n'.join([part1, part2, part3])
    else:
        return header

def format_number(num):
    if isinstance(num, (int, float)) and num.is_integer():
        return int(num)
    return num

def shrink_table_until_fit(data, available_width=width - 2 * margin, 
                           start_body_size=body_font_size, start_header_size=Header_font_size, 
                           min_font=4, step=0.5):
    body_size = start_body_size
    header_size = start_header_size
    from reportlab.platypus import Table, TableStyle
    while True:
        t = Table(data, rowHeights=row_heights)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('INNERGRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('FONT', (0, 0), (-1, 0), 'ArabicFont'),
            ('FONT', (0, 1), (-1, -1), 'ArabicFont'),
            ('FONTSIZE', (0, 0), (-1, 0), header_size),
            ('FONTSIZE', (0, 1), (-1, -1), body_size),
        ]))
        w, h = t.wrapOn(None, 0, 0)
        if w <= available_width or body_size <= min_font:
            return t  
        body_size -= step
        header_size -= step

def dataframe_to_table(df, student, semester, exclude_last_column=False):
    full_grade = []
    student_data = []
    full_mark = 0 
    student_mark = 0 
    col_names = df.columns.tolist()

    if exclude_last_column:
        col_names = col_names[:-1]
        full_grade = df.iloc[0, 2:-1].tolist()
        student_data = df.iloc[student, 2:-1].tolist()
    else:
        full_grade = df.iloc[0, 2:].tolist()
        student_data = df.iloc[student, 2:].tolist()

    table_heads = [process_arabic_text(split_line_into_two_parts(col)) for col in col_names]  
    fail = ['-'] * len(full_grade)
    full_grade = [format_number(num) for num in full_grade]
    student_data = [format_number(num) for num in student_data]

    for count, score in enumerate(student_data):
        col_name = str(col_names[count])  
        half_mark = full_grade[count] / 2
        if any(key in col_name for key in ["طقس", "قبطي", "طقس شفوي", "قبطي شفوي", "قبطي شفوى", "طقس شفوى", "قبطى"]):
            if score < int(half_mark):
                fail[count] = 'X'
        else:
            if score < half_mark:
                fail[count] = 'X'

    for i in range(len(full_grade)):
        full_mark += full_grade[i]
        student_mark += student_data[i]

    percent = format_number(round((student_mark / full_mark) * 100, 2))
    table_heads.append(process_arabic_text("المجموع"))
    full_grade.append(format_number(full_mark))
    student_data.append(format_number(student_mark))
    fail.append(f"{percent}%")
    table_heads.insert(2, process_arabic_text(semester))
    full_grade.insert(0, process_arabic_text("الدرجة الكلية"))
    student_data.insert(0, process_arabic_text("الدرجة"))
    fail.insert(0, process_arabic_text("يعني اعادة 'X'"))
    data = [table_heads[2:][::-1]] + [full_grade[::-1]] + [student_data[::-1]] + [fail[::-1]]
    t = shrink_table_until_fit(data)
    return t, full_mark, student_mark

def draw_page_border(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(2)
    canvas.rect(margin, margin, width - 2*margin, height - 2*margin)
    header_text_1 = "بطريركية الأقباط الأرثوذوكس"  
    header_text_2 = "كنيسة السيدة العذراء والشهيد مارجرجس بغبريال"
    header_text_3 = "مدرسة الشهيد استفانوس"
    font_size = 25 
    text_margin = 35
    bidi_text_1 = process_arabic_text(header_text_1)
    bidi_text_2 = process_arabic_text(header_text_2)
    bidi_text_3 = process_arabic_text(header_text_3)
    canvas.setFont("ArabicFont", font_size)
    space = 70
    canvas.drawCentredString(width / 2, height - space, bidi_text_1)
    canvas.drawCentredString(width / 2, height - space - text_margin, bidi_text_2)
    canvas.drawCentredString(width / 2, height - space - text_margin * 2, bidi_text_3)
    logo_path = ".\\talmaza_logo.jpg"
    logo_width, logo_height = 130, 130
    logo_x = width - logo_width - margin - 10  
    logo_y = height - logo_height - margin - 10  
    canvas.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height)
    data = [
        [process_arabic_text(student_name), process_arabic_text("الاسم")],
        [str(student_id), process_arabic_text("ID")],
        [process_arabic_text(student_class), process_arabic_text("الفصل")],
        [process_arabic_text(student_level), process_arabic_text("المستوي")]
    ]
    from reportlab.platypus import Table, TableStyle
    table = Table(data, rowHeights=25)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('INNERGRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('FONT', (0, 0), (-1, -1), 'ArabicFont'),
        ('FONTSIZE', (0, 0), (-1, 0), 13),
        ('FONTSIZE', (0, 1), (-1, -1), 14)
    ]))
    table.wrapOn(canvas, width, height)
    table.drawOn(canvas, margin + 10, height - margin - 120)
    canvas.restoreState()

def create_table(df):
    from reportlab.platypus import Table, TableStyle
    table = Table(df, rowHeights=22)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('INNERGRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('FONT', (0, 0), (-1, -1), 'ArabicFont'),
        ('FONTSIZE', (0, 0), (-1, -1), 15)
    ]))
    return table

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")    

def run_main(folder_path, terms_to_print):
    global student_class, student_level, student_name, student_id
    excel_files = [os.path.join(folder_path, f) 
               for f in os.listdir(folder_path) if f.endswith('.xlsx')]
    
    for file_path in excel_files:
        base_name = os.path.splitext(os.path.basename(file_path))[0]                
        combined_pdf    =           base_name  + ".pdf"
        base_parts = base_name.split()                             
        if "المستوي" in base_name and base_parts[0] != "المستوي":
            parts = base_name.split("المستوي", 1)   
            student_class = parts[0].strip()
            student_level = "المستوي " + parts[1].strip()
        else:
            student_class = base_name
            student_level = base_name

        dfs = {}
        for term in terms_to_print:
            try:
                dfs[term] = pd.read_excel(file_path, sheet_name=term).fillna(0)
            except Exception:
                print(f"Sheet {term} not found in {file_path}, skipping.")
                continue

        for row in range(1, len(dfs['Term_1'])):
            student_name = str(dfs['Term_1'].iloc[row, 1])
            student_id = int(dfs['Term_1'].iloc[row, 0])
            pdf_filename = os.path.join(single_pdf_out, f"{student_name}.pdf")
            doc = SimpleDocTemplate(pdf_filename, pagesize=landscape(A4))
            total_mark, total_student = 0, 0
            transcript = []
            transcript.append(Spacer(1, 85))
            for term in terms_to_print:
                if term not in dfs:   # ✅ Skip if sheet not found
                    continue
                df = dfs[term]
                semester_name = (
                    "الترم الاول" if term == "Term_1" else
                    "الترم الثاني" if term == "Term_2" else
                    "الترم الثالث"
                )
                exclude_last = False
                if term == "Term_3":
                    last_col_name = str(df.columns[-1]).strip().lower()
                    if last_col_name == "bonus":
                        exclude_last = True
                table, full_mark, student_mark = dataframe_to_table(
                    df, row, semester_name, exclude_last_column=exclude_last
                )
                transcript.append(table)
                total_mark += full_mark
                total_student += student_mark
                transcript.append(Spacer(1, space_between_tables))
            bonus = 0
            if "Term_3" in dfs:
                bonus = format_number(dfs["Term_3"].iloc[row, -1])
            percent = format_number(round(((total_student + bonus) / total_mark) * 100, 2))
            df_4 = [
                [process_arabic_text("النسبة"), process_arabic_text("المجموع الكلي"), process_arabic_text("مجموعك + Bonus"), process_arabic_text("Bonus")],
                [f"{percent}%", format_number(total_mark), format_number(total_student + bonus), bonus]
            ]
            table_4 = create_table(df_4)
            transcript.append(table_4)
            doc.build(transcript, onFirstPage=draw_page_border, onLaterPages=draw_page_border)
            students_data.append((pdf_filename, student_name, percent))

        students_data.sort(key=lambda x: x[2], reverse=True)
        merger = PdfMerger()
        for pdf_filename, student_name, percent in students_data:
            merger.append(pdf_filename)
        output_filename = os.path.join(output_dir, combined_pdf)
        merger.write(output_filename)
        merger.close()
        print(f"All PDFs merged successfully for {process_arabic_text(base_name)}")
        for pdf_filename, student_name, percent in students_data:
            os.remove(pdf_filename)
        students_data.clear()
    print("All done!")


# ==========================
#            GUI
# ==========================

# ---------------- Redirect print to GUI ----------------
class TextRedirector:
    def __init__(self, widget):
        self.widget = widget

    def write(self, msg):
        self.widget.configure(state="normal")
        self.widget.insert(tk.END, msg)
        self.widget.see(tk.END)  # auto-scroll
        self.widget.configure(state="disabled")

    def flush(self):
        pass  # required for sys.stdout compatibility

# ---------------- Main GUI ----------------
def launch_gui():
    root = tk.Tk()
    root.title("📑 Shehadat EL Talmaza Generator")
    root.geometry("800x600")
    root.configure(bg="#f0f2f5")

    # Title
    title_label = tk.Label(
        root,
        text="Shehadat EL Talmaza Generator",
        font=("Arial", 20, "bold"),
        bg="#f0f2f5",
        fg="#2c3e50"
    )
    title_label.pack(pady=15)

    # Folder selection
    folder_frame = ttk.LabelFrame(root, text="Select Folder", padding=10)
    folder_frame.pack(fill="x", padx=20, pady=10)

    folder_var = tk.StringVar(value=".\\Classes")

    folder_entry = ttk.Entry(folder_frame, textvariable=folder_var, width=70)
    folder_entry.grid(row=0, column=0, padx=5, pady=5, sticky="w")

    def browse_folder():
        folder_selected = filedialog.askdirectory(initialdir=".")
        if folder_selected:
            folder_var.set(folder_selected)

    browse_btn = ttk.Button(folder_frame, text="Browse", command=browse_folder)
    browse_btn.grid(row=0, column=1, padx=5, pady=5)

    # Term selection frame
    term_frame = ttk.LabelFrame(root, text="Select Terms", padding=10)
    term_frame.pack(fill="x", padx=20, pady=10)

    term_vars = {
        "Term_1": tk.BooleanVar(value=True),
        "Term_2": tk.BooleanVar(value=True),
        "Term_3": tk.BooleanVar(value=True),
    }

    for i, (term, var) in enumerate(term_vars.items()):
        ttk.Checkbutton(term_frame, text=term, variable=var).grid(
            row=0, column=i, padx=10, pady=5
        )

    # Run + Clear buttons frame
    btn_frame = tk.Frame(root, bg="#f0f2f5")
    btn_frame.pack(pady=10)

    def run_script():
        status_label.config(text="⏳ Running...", foreground="blue")

        def task():
            global terms_to_print, folder_path
            terms_to_print = [t for t, v in term_vars.items() if v.get()]
            folder_path = folder_var.get() or ".\\Classes"

            if not os.path.exists(folder_path):
                print("Invalid folder selected")
                status_label.config(text="Invalid folder", foreground="red")
                return

            try:
                run_main(folder_path, terms_to_print)   # <-- your original script function
                status_label.config(text="Completed!", foreground="green")
            except Exception as e:
                print(f"Error: {e}")
                status_label.config(text="Error occurred", foreground="red")

        threading.Thread(target=task).start()

    run_btn = tk.Button(
        btn_frame,
        text="Genrate",
        font=("Arial", 14, "bold"),
        bg="#27ae60",
        fg="white",
        relief="flat",
        command=run_script
    )
    run_btn.grid(row=0, column=0, padx=10)

    def clear_logs():
        log_text.configure(state="normal")
        log_text.delete("1.0", tk.END)
        log_text.configure(state="disabled")

    clear_btn = tk.Button(
        btn_frame,
        text="Clear Screen",
        font=("Arial", 14, "bold"),
        bg="#e74c3c",
        fg="white",
        relief="flat",
        command=clear_logs
    )
    clear_btn.grid(row=0, column=1, padx=10)

    # Log frame
    log_frame = ttk.LabelFrame(root, text="Execution Log", padding=10)
    log_frame.pack(fill="both", expand=True, padx=20, pady=10)

    log_text = scrolledtext.ScrolledText(
        log_frame,
        wrap=tk.WORD,
        height=15,
        font=("Consolas", 10),
        bg="black",
        fg="lime",
        insertbackground="white"
    )
    log_text.pack(fill="both", expand=True)

    sys.stdout = TextRedirector(log_text)
    sys.stderr = TextRedirector(log_text)

    # Status bar
    status_label = tk.Label(
        root,
        text="✅ Ready",
        anchor="w",
        bg="#2c3e50",
        fg="white",
        font=("Arial", 10)
    )
    status_label.pack(fill="x", side="bottom")

    root.mainloop()

# ---------------- Run GUI ----------------
if __name__ == "__main__":
    launch_gui()