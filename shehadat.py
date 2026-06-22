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

# Changeable variables
output_dir      =   ".\\out"                          # folder to save the combined pdfs
single_pdf_out  =   ".\\single"                       # folder to save each student pdf untill they are combined and then deleted
# file_path       =   '.\\Classes\\اولي ابتدائي المستوي 1 السنة 1.xlsx'     # the 4th semester file path
folder_path = '.\\Classes'
excel_files = [os.path.join(folder_path, f) 
               for f in os.listdir(folder_path) if f.endswith('.xlsx')]


space_between_tables = 15
row_heights = 22
Header_font_size=   11        # 6  7  9                     # the font size of the header
body_font_size  =   13        # 8  9  11                       # the font size of the body
terms_to_print = ["Term_1", "Term_2", "Term_3"]  # list of sheet names to print

# Create the output directory
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

# Register the Arabic font
pdfmetrics.registerFont(TTFont('ArabicFont', 'times.ttf'))

# Adjust the location variables
margin = 15  
width, height = landscape(A4)

# 3 semesters sum variables
total_mark = 0
total_student = 0
student_name = ""
student_id = 0

# List to store student details (filename, name, percent)
students_data = []

# Function to reshape and reorder Arabic text
def process_arabic_text(text):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

# Example function to split line into two parts without corrupting meaning
def split_line_into_two_parts(header):
    words = header.split(' ')  # Split by spaces to maintain word integrity
    if len(words) > 1:  # If there are more than one word in the
        midpoint = len(words) // 2  # Find the midpoint index of words

        # Join the first and second halves with '\n' separator
        first_half = ' '.join(words[:midpoint])
        second_half = ' '.join(words[midpoint:])
        return '\n'.join([first_half, second_half])
    else:
        return header

def split_line_into_three_parts(header):
    words = header.split('_')  # Split by spaces to maintain word integrity
    if len(words) > 1:  # If there are more than one word in the
        part1_end = len(words) // 3
        part2_end = 2 * (len(words) // 3)

        # Join the first and second and third parts with '\n' separator
        part1 = ' '.join(words[:part1_end])
        part2 = ' '.join(words[part1_end:part2_end])
        part3 = ' '.join(words[part2_end:])
        return '\n'.join([part1, part2, part3])
    else:
        return header

# Format numbers directly in the table rendering
def format_number(num):
    if isinstance(num, (int, float)) and num.is_integer():
        # Format number to remove unnecessary decimal points and trailing zeros
        return int(num)
    return num

def shrink_table_until_fit(data, available_width=width - 2 * margin, 
                           start_body_size=body_font_size, start_header_size=Header_font_size, 
                           min_font=4, step=0.5):
    """
    Make a table that shrinks font size until it fits in available_width.
    """
    body_size = start_body_size
    header_size = start_header_size

    while True:
        # Build table with current font sizes
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

        # Let ReportLab calculate the natural width
        w, h = t.wrapOn(None, 0, 0)

        if w <= available_width or body_size <= min_font:
            return t  # fits, or too small to shrink further

        # Shrink a bit more
        body_size -= step
        header_size -= step

# Function to convert dataframe to reportlab Table
def dataframe_to_table(df, student, semester, exclude_last_column=False):
    # Create a list of lists to store the data of the heads and render the Arabic text
    full_grade = []
    student_data = []
    full_mark = 0 # variable to save the sum of the full_grade list
    student_mark = 0 # variable to save the sum of the student_data list
    col_names = df.columns.tolist()

    if exclude_last_column:
        col_names = col_names[:-1]
        full_grade = df.iloc[0, 2:-1].tolist()
        student_data = df.iloc[student, 2:-1].tolist()
    else:
        full_grade = df.iloc[0, 2:].tolist()
        student_data = df.iloc[student, 2:].tolist()

    table_heads = [process_arabic_text(split_line_into_two_parts(col)) for col in col_names]  # to make the head be written virtically use '\n'.join(col.split())
    fail = ['-'] * len(full_grade)

    full_grade = [format_number(num) for num in full_grade]
    student_data = [format_number(num) for num in student_data]

    # # Detect the fail subjects
    # for count, score in enumerate(student_data):
    #     if score < int(full_grade[count] / 2):
    #         fail[count] = 'X'

    for count, score in enumerate(student_data):
        col_name = str(col_names[count])  # get column name for subject
        half_mark = full_grade[count] / 2

        # Special handling for specific subjects
        if any(key in col_name for key in ["طقس", "قبطي", "طقس شفوي", "قبطي شفوي", "قبطي شفوى", "طقس شفوى", "قبطى"]):
            # Compare with integer half
            if score < int(half_mark):
                fail[count] = 'X'
        else:
            # Compare with exact half
            if score < half_mark:
                fail[count] = 'X'


    # Get the total
    for i in range(len(full_grade)):
        full_mark += full_grade[i]
        student_mark += student_data[i]

    percent = format_number(round((student_mark / full_mark) * 100, 2))

    # Add the sum column
    table_heads.append(process_arabic_text("المجموع"))
    full_grade.append(format_number(full_mark))
    student_data.append(format_number(student_mark))
    fail.append(f"{percent}%")

    # Add the info column
    table_heads.insert(2, process_arabic_text(semester))
    full_grade.insert(0, process_arabic_text("الدرجة الكلية"))
    student_data.insert(0, process_arabic_text("الدرجة"))
    fail.insert(0, process_arabic_text("يعني اعادة 'X'"))

    data = [table_heads[2:][::-1]] + [full_grade[::-1]] + [student_data[::-1]] + [fail[::-1]]
    
    # t = Table(data, rowHeights=row_heights)
    t = shrink_table_until_fit(data)


    # t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    #                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    #                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    #                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    #                        ('INNERGRID', (0, 0), (-1, -1), 1, colors.black),
    #                        ('BOX', (0, 0), (-1, -1), 1, colors.black),
    #                        ('FONT', (0, 0), (-1, -1), 'ArabicFont'),
    #                        ('FONTSIZE', (0, 0), (-1, 0), Header_font_size),  
    #                        ('FONTSIZE', (1, 1), (-1, -1), body_font_size)    
    #                        ]))
    return t, full_mark, student_mark

# Function to add a page border, header text in Arabic, and a table in the top left corner
def draw_page_border(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(2)
    canvas.rect(margin, margin, width - 2*margin, height - 2*margin)
    
    # Add header text in Arabic
    header_text_1 = "بطريركية الأقباط الأرثوذوكس"  
    header_text_2 = "كنيسة السيدة العذراء والشهيد مارجرجس بغبريال"
    header_text_3 = "مدرسة الشهيد استفانوس"
    
    font_size = 25 # header font size
    text_margin = 35
    # Correct shaping and direction
    bidi_text_1 = process_arabic_text(header_text_1)
    bidi_text_2 = process_arabic_text(header_text_2)
    bidi_text_3 = process_arabic_text(header_text_3)
    
    canvas.setFont("ArabicFont", font_size)
    space = 70
    canvas.drawCentredString(width / 2, height - space, bidi_text_1)
    canvas.drawCentredString(width / 2, height - space - text_margin, bidi_text_2)
    canvas.drawCentredString(width / 2, height - space - text_margin * 2, bidi_text_3)

    # Insert logo
    logo_path = ".\\talmaza_logo.jpg"
    logo_width, logo_height = 130, 130
    logo_x = width - logo_width - margin - 10  # Adjust the x-coordinate
    logo_y = height - logo_height - margin - 10  # Adjust the y-coordinate
    canvas.drawImage(logo_path, logo_x, logo_y, width=logo_width, height=logo_height)

    # image_path = "H:\Talmaza\semester.png"
    # image_width, image_height = 500, 70
    # image_x = (width - image_width) / 2  # Adjust the x-coordinate
    # image_y = height - logo_height - margin - 80  # Adjust the y-coordinate
    # canvas.drawImage(image_path, image_x, image_y, width=image_width, height=image_height)

    # Draw a table in the top-left corner
    data = [
        [process_arabic_text(student_name), process_arabic_text("الاسم")],
        [str(student_id), process_arabic_text("ID")],
        [process_arabic_text(student_class), process_arabic_text("الفصل")],
        [process_arabic_text(student_level), process_arabic_text("المستوي")]
    ]
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
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")          # to print Arabic in the terminal

for file_path in excel_files:

    base_name = os.path.splitext(os.path.basename(file_path))[0]                # the base name of the file without extension
    combined_pdf    =           base_name  + ".pdf"                             # the name of the combined pdf

    base_parts = base_name.split()
    if "المستوي" in base_name and base_parts[0] != "المستوي":
        parts = base_name.split("المستوي", 1)   # split only at first occurrence
        student_class = parts[0].strip()
        student_level = "المستوي " + parts[1].strip()
    else:
        # fallback if 'المستوي' not in name
        student_class = base_name
        student_level = base_name



    # Load all terms for this file
    dfs = {}
    for term in terms_to_print:
        try:
            dfs[term] = pd.read_excel(file_path, sheet_name=term).fillna(0)
        except Exception:
            print(f"Sheet {term} not found in {file_path}, skipping.")
            continue


    for row in range(1, len(dfs['Term_1'])):
        # Create a PDF document
        student_name = str(dfs['Term_1'].iloc[row, 1])
        student_id = int(dfs['Term_1'].iloc[row, 0])
        pdf_filename = os.path.join(single_pdf_out, f"{student_name}.pdf")
        doc = SimpleDocTemplate(pdf_filename, pagesize=landscape(A4))
        total_mark, total_student = 0, 0
        transcript = []

        # Add space after the logo
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

            # For the 3rd term → exclude last column only if its name is "bonus" (case-insensitive)
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

        # Build PDF document with the border and header text in Arabic
        doc.build(transcript, onFirstPage=draw_page_border, onLaterPages=draw_page_border)
        # print(f"PDF generated successfully: {pdf_filename}")

        # Store student data: filename, student name, and percentage
        students_data.append((pdf_filename, student_name, percent))

    # Sort students by percent in descending order
    students_data.sort(key=lambda x: x[2], reverse=True)

    # Merge all PDFs into one
    merger = PdfMerger()

    for pdf_filename, student_name, percent in students_data:
        merger.append(pdf_filename)

    output_filename = os.path.join(output_dir, combined_pdf)
    merger.write(output_filename)
    merger.close()

    
    print(f"All PDFs merged successfully for {base_name}")



    # Delete the individual PDFs
    for pdf_filename, student_name, percent in students_data:
        os.remove(pdf_filename)
        # print(f"Deleted file: {pdf_filename}")

    # Clear list for next file
    students_data.clear()