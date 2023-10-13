import customtkinter as tk
import json
import os
import subprocess

def save_choice():
    selected_company = company_var.get()
    if selected_company and selected_company != "None":
        with open("sel.json", "w") as file:
            json.dump({"sel": selected_company}, file)
        root.quit()
        root.destroy()
        os.environ["LAUNCHED_FROM_LAUNCH_PY"] = "True"
        subprocess.run(["python", "main.py"])

def center_window(root, width, height):
    # Obtém a resolução da tela
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Calcula as coordenadas x e y para centralizar a janela
    x = (screen_width / 2) - (width / 2)
    y = (screen_height / 2) - (height / 2)

    root.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

def toggle_button_state():
    selected_company = company_var.get()
    if selected_company and selected_company != "None":
        warning_label.pack_forget()
        button.configure(state="normal")
    else:
        warning_label.pack(pady=10)
        button.configure(state="disabled")

root = tk.CTk()
root.title("")
root.geometry("175x160")
root.resizable(False, False)

center_window(root, 175, 200)

label = tk.CTkLabel(root, font=('Helvetica', 16, 'bold'), text="Selecione a empresa:")
label.pack(pady=10)

# Adicionando um label de aviso
warning_label = tk.CTkLabel(root, text="Por favor, selecione uma empresa.")
warning_label.pack_forget()  

company_var = tk.StringVar(value="None")

companies = ["Maggiore Modas","Maggiore Pecas", "Brilha Natal"]

# Adicionar o comando toggle_button_state ao CTkRadioButton
for company in companies:
    tk.CTkRadioButton(root, font=('Helvetica', 14, 'bold'), border_color='#4d7cff', radiobutton_height=15, radiobutton_width=15, border_width_checked=4, text=company, variable=company_var, value=company, command=toggle_button_state).pack(pady=5)

# Botão inicialmente desabilitado
button = tk.CTkButton(root, font=('Helvetica', 20, 'bold'), text_color_disabled='#808080', text_color='white',text="Confirmar", fg_color='black', border_width=2, border_color='#4d7cff', command=save_choice, state="disabled", width=34, height=23)
button.pack(pady=10)

toggle_button_state()

root.mainloop()