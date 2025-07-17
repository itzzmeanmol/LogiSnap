import os
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageFilter
from predict import predict_image, batch_predict
import qrcode
import tempfile
import platform
import subprocess

# --- Resolve Base Directory ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
bg_path = os.path.join(BASE_DIR, "background.jpg")

# --- Main Application Setup ---
app = tb.Window(themename="cosmo")
app.title("LogiSnap")
app.state("zoomed")

# --- Background ---
try:
    bg_img = Image.open(bg_path).resize((app.winfo_screenwidth(), app.winfo_screenheight()))
    bg_img = bg_img.filter(ImageFilter.GaussianBlur(15))
    bg_photo = ImageTk.PhotoImage(bg_img)

    bg_label = tb.Label(app, image=bg_photo)
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)
    bg_label.lower()
except FileNotFoundError:
    messagebox.showwarning("Background Not Found", f"{bg_path} not found.")

# (The rest of the file remains unchanged...)


overlay = tb.Frame(app, bootstyle="light")
overlay.place(relx=0.5, rely=0.5, anchor='center', relwidth=0.9, relheight=0.9)

# --- Main Layout ---
main_frame = tb.Frame(overlay)
main_frame.pack(expand=True, fill=BOTH, padx=20, pady=20)
main_frame.grid_columnconfigure((0, 1), weight=1)
main_frame.grid_rowconfigure(1, weight=1)

# --- Title ---
title_label = tb.Label(main_frame, text="🪖 LogiSnap", font=("Segoe UI", 28, "bold"), bootstyle="dark")
title_label.grid(row=0, column=0, columnspan=2, pady=(10, 20))

# --- Left (Image) ---
left_frame = tb.Frame(main_frame)
left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

image_display_frame = tb.Labelframe(left_frame, text="Image Preview", bootstyle="primary")
image_display_frame.pack(expand=True, fill=BOTH)

canvas_label = tb.Label(image_display_frame, text="Upload an image to begin", font=("Segoe UI", 14, "italic"), bootstyle="secondary")
canvas_label.pack(expand=True)
canvas = tb.Canvas(image_display_frame, width=400, height=400, bg="white", bd=0, highlightthickness=0)

# --- Right (Result) ---
right_frame = tb.Frame(main_frame)
right_frame.grid(row=1, column=1, sticky="nsew", padx=(10, 0))

result_frame = tb.Labelframe(right_frame, text="Prediction Details", bootstyle="primary")
result_frame.pack(expand=True, fill=BOTH)

result_label = tb.Label(result_frame, text="", font=("Segoe UI", 16, "bold"), bootstyle="info")
result_label.pack(pady=(5, 10), anchor="w", padx=10)

details_label = tb.Label(result_frame, text="", font=("Segoe UI", 12), wraplength=450, justify="left", bootstyle="dark")
details_label.pack(pady=5, anchor="w", fill="x", padx=10)

confidence_label = tb.Label(result_frame, text="", font=("Segoe UI", 11, "italic"), bootstyle="warning")
confidence_label.pack(pady=(0, 10), anchor="w", padx=10)

qr_frame = tb.Labelframe(right_frame, text="QR Code", bootstyle="primary")
qr_frame.pack(fill="x", pady=(10, 0))
qr_canvas = tb.Canvas(qr_frame, width=180, height=180, bg="white", bd=0, highlightthickness=0)
qr_canvas.pack(pady=10, padx=10)

# --- Buttons ---
btn_frame = tb.Frame(main_frame)
btn_frame.grid(row=2, column=0, columnspan=2, pady=20, sticky="ew")

# --- Global State ---
current_qr_image = None
batch_results = []
current_index = 0

# --- Functions ---
def display_result(file_path, details=None):
    global current_qr_image
    try:
        canvas_label.pack_forget()
        canvas.pack(expand=True, padx=5, pady=5)
        img = Image.open(file_path).resize((400, 400), Image.LANCZOS)
        img_tk = ImageTk.PhotoImage(img)
        canvas.create_image(200, 200, image=img_tk)
        canvas.image = img_tk

        if details is None:
            predicted_class, nomenclature, cat_no, part_no, confidence = predict_image(file_path)
        else:
            predicted_class, nomenclature, cat_no, part_no, confidence = details['class'], details['nomenclature'], details['cat_no'], details['part_no'], details['confidence']

        result_label.config(text=f"🛠️ Category: {predicted_class}")
        details_label.config(text=f"• Nomenclature: {nomenclature}\n• Cat No: {cat_no}\n• Part No: {part_no}")
        confidence_label.config(text=f"Confidence: {confidence:.2f}" if predicted_class != "No Match Found" else "Confidence: Low")

        if predicted_class != "No Match Found":
            qr_data = f"Class: {predicted_class}\nNomenclature: {nomenclature}\nCat No: {cat_no}\nPart No: {part_no}"
            qr = qrcode.make(qr_data).resize((180, 180), Image.LANCZOS)
            qr_img = ImageTk.PhotoImage(qr)
            qr_canvas.create_image(90, 90, image=qr_img)
            qr_canvas.image = qr_img
            current_qr_image = qr
        else:
            qr_canvas.delete("all")
            current_qr_image = None

    except Exception as e:
        messagebox.showerror("Error", f"Prediction failed:\n{str(e)}")
        clear_canvas()

def browse_image():
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
    if file_path:
        next_btn.config(state="disabled")
        prev_btn.config(state="disabled")
        display_result(file_path)

def clear_canvas():
    canvas.delete("all")
    canvas.pack_forget()
    canvas_label.pack(expand=True)
    result_label.config(text="")
    details_label.config(text="")
    confidence_label.config(text="")
    qr_canvas.delete("all")
    global current_qr_image, batch_results, current_index
    current_qr_image = None
    batch_results = []
    current_index = 0
    next_btn.config(state="disabled")
    prev_btn.config(state="disabled")

def print_qr():
    if current_qr_image:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                current_qr_image.save(tmp.name)
            if platform.system() == "Windows":
                os.startfile(tmp.name, "print")
            elif platform.system() == "Darwin":
                subprocess.run(["lp", tmp.name])
            else:
                subprocess.run(["xdg-open", tmp.name])
        except Exception as e:
            messagebox.showerror("Print Error", str(e))
    else:
        messagebox.showinfo("No QR Code", "No QR code available.")

def batch_predict_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        global batch_results, current_index
        try:
            batch_results = batch_predict(folder_path)
            if not batch_results:
                messagebox.showinfo("No Images Found", "No valid images found.")
                return
            current_index = 0
            show_batch_result()
        except Exception as e:
            messagebox.showerror("Batch Error", f"Error during batch prediction:\n{str(e)}")

def show_batch_result():
    result_data = batch_results[current_index]
    display_result(result_data['image'], result_data)
    update_nav_buttons()

def update_nav_buttons():
    prev_btn.config(state="normal" if current_index > 0 else "disabled")
    next_btn.config(state="normal" if current_index < len(batch_results) - 1 else "disabled")

def show_nav(direction):
    global current_index
    new_index = current_index + direction
    if 0 <= new_index < len(batch_results):
        current_index = new_index
        show_batch_result()

def create_button(parent, text, command, bootstyle, state="normal"):
    return tb.Button(parent, text=text, command=command, bootstyle=bootstyle, width=15, state=state)

upload_btn = create_button(btn_frame, "📤 Upload", browse_image, "success")
batch_btn = create_button(btn_frame, "📁 Batch", batch_predict_folder, "info")
clear_btn = create_button(btn_frame, "🧹 Clear", clear_canvas, "danger")
prev_btn = create_button(btn_frame, "⬅️ Prev", lambda: show_nav(-1), "secondary-outline", "disabled")
next_btn = create_button(btn_frame, "Next ➡️", lambda: show_nav(1), "secondary-outline", "disabled")
print_btn = create_button(btn_frame, "🖨️ Print QR", print_qr, "primary-outline")

btn_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
upload_btn.grid(row=0, column=0, padx=5)
batch_btn.grid(row=0, column=1, padx=5)
prev_btn.grid(row=0, column=2, padx=5)
next_btn.grid(row=0, column=3, padx=5)
clear_btn.grid(row=0, column=4, padx=5)
print_btn.grid(row=0, column=5, padx=5)

# --- Run App ---
app.mainloop()
