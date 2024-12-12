import sqlite3
import flet as ft

class ResourceReservationSystem:
    def __init__(self, db_name="reservation_system.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self._initialize_db()

    def _initialize_db(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                available INTEGER DEFAULT 1
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER,
                user_name TEXT NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (resource_id) REFERENCES resources (id)
            )
        """)
        self.connection.commit()

    def reset_db(self):
        self.cursor.execute("DROP TABLE IF EXISTS resources")
        self.cursor.execute("DROP TABLE IF EXISTS reservations")
        self._initialize_db()
        self.connection.commit()

    def _generate_resource_id(self):
        self.cursor.execute("SELECT MAX(id) FROM resources")
        max_id = self.cursor.fetchone()[0]
        return 1 if max_id is None else max_id + 1

    def add_resource(self, name, description):
        new_id = self._generate_resource_id()
        self.cursor.execute(
            "INSERT INTO resources (id, name, description) VALUES (?, ?, ?)", (new_id, name, description)
        )
        self.connection.commit()

    def view_resources(self):
        self.cursor.execute("SELECT * FROM resources")
        return self.cursor.fetchall()

    def update_resource(self, resource_id, name=None, description=None, available=None):
        updates = []
        params = []
        if name:
            updates.append("name = ?")
            params.append(name)
        if description:
            updates.append("description = ?")
            params.append(description)
        if available is not None:
            updates.append("available = ?")
            params.append(available)

        params.append(resource_id)
        update_query = f"UPDATE resources SET {', '.join(updates)} WHERE id = ?"
        self.cursor.execute(update_query, params)
        self.connection.commit()

    def delete_resource(self, resource_id):
        self.cursor.execute("DELETE FROM reservations WHERE resource_id = ?", (resource_id,))
        self.cursor.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
        self._reassign_ids()
        self.connection.commit()

    def _reassign_ids(self):
        self.cursor.execute("SELECT id FROM resources ORDER BY id")
        resources = self.cursor.fetchall()
        for index, (old_id,) in enumerate(resources, start=1):
            self.cursor.execute("UPDATE resources SET id = ? WHERE id = ?", (index, old_id))
            self.cursor.execute("UPDATE reservations SET resource_id = ? WHERE resource_id = ?", (index, old_id))
        self.connection.commit()

    def create_reservation(self, resource_id, user_name, date):
        try:
            if not user_name.strip():
                return False

            self.cursor.execute("SELECT id, available FROM resources WHERE id = ?", (resource_id,))
            resource = self.cursor.fetchone()

            if not resource:
                print("Resource does not exist.")
                return False

            if resource[1] == 0:  # Check if the resource is unavailable
                print("Resource is not available.")
                return False

            self.cursor.execute(
                "INSERT INTO reservations (resource_id, user_name, date) VALUES (?, ?, ?)",
                (resource_id, user_name, date)
            )
            self.cursor.execute("UPDATE resources SET available = 0 WHERE id = ?", (resource_id,))
            self.connection.commit()
            print("Reservation created successfully.")
            return True

        except sqlite3.Error as e:
            print(f"Database error during reservation: {e}")
            return False

    def view_reservations(self):
        self.cursor.execute("""
            SELECT r.id, r.resource_id, r.user_name, r.date, res.name 
            FROM reservations r 
            JOIN resources res ON r.resource_id = res.id
        """)
        return self.cursor.fetchall()

def main(page: ft.Page):
    page.title = "Resource Reservation System"
    db = ResourceReservationSystem()

    # Apply gradient background
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.LinearGradient(
    begin=ft.alignment.top_left,
    end=ft.alignment.bottom_right,
    colors=["#FF5733", "#FFC300"]
    )


    button_style = ft.ButtonStyle(
        padding=20,
        bgcolor=ft.Colors.PURPLE,
        color=ft.Colors.WHITE
    )

    def show_resource_ui():
        resources = db.view_resources()
        resource_ui.controls.clear()
        for resource in resources:
            availability = "Available" if resource[3] == 1 else "Unavailable"
            resource_ui.controls.append(
                ft.Row([ft.Text(f"ID: {resource[0]} | Name: {resource[1]} | Description: {resource[2]} | Status: {availability}"),
                        ft.ElevatedButton("Remove", on_click=lambda e, rid=resource[0]: remove_resource_ui(rid), style=button_style)])
            )
        page.update()

    def show_reservations_ui():
        reservations = db.view_reservations()
        reservations_ui.controls.clear()
        for res in reservations:
            reservations_ui.controls.append(
                ft.Row([
                    ft.Text(f"Resource: {res[4]}, Reserved by: {res[2]} on {res[3]}"),
                    ft.ElevatedButton(
                        "Remove", 
                        on_click=lambda e, rid=res[0], res_id=res[1]: remove_reservation_ui(rid, res_id),
                        style=button_style)
                ])
            )
        page.update()

    def add_resource_ui(e):
        name = resource_name.value
        description = resource_description.value
        if name and description:
            db.add_resource(name, description)
            resource_name.value = ""
            resource_description.value = ""
            show_resource_ui()

    def reserve_resource_ui(e):
        resource_id = reserve_resource_id.value.strip()
        user_name = reserve_user_name.value.strip()
        date = reserve_date.value.strip()

        if not resource_id or not user_name or not date:
            reserve_feedback.value = "All fields are required."
            page.update()
            return

        success = db.create_reservation(resource_id, user_name, date)
        if success:
            reserve_feedback.value = "Reservation successful!"
            reserve_feedback.color = "green"  # Set color to green for success messages
        else:
            reserve_feedback.value = "Failed to reserve: Resource unavailable or does not exist."
            reserve_feedback.color = "red"  # Set color to red for error messages

        reserve_resource_id.value = ""
        reserve_user_name.value = ""
        reserve_date.value = ""
        show_resource_ui()
        page.update()

    def remove_resource_ui(resource_id):
        db.delete_resource(resource_id)
        show_resource_ui()

    def remove_reservation_ui(reservation_id, resource_id):
        db.cursor.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
        db.update_resource(resource_id, available=1)
        show_reservations_ui()

    def show_list_ui():
        resources = db.view_resources()
        reservations = db.view_reservations()
        list_ui.controls.clear()
        list_ui.controls.append(ft.Text("Resources:"))
        for resource in resources:
            availability = "Available" if resource[3] == 1 else "Unavailable"
            list_ui.controls.append(
                ft.Text(f"ID: {resource[0]} | Name: {resource[1]} | Description: {resource[2]} | Status: {availability}")
            )
        list_ui.controls.append(ft.Text("Reservations:"))
        for res in reservations:
            list_ui.controls.append(
                ft.Text(f"Resource: {res[4]} | Reserved by: {res[2]} on {res[3]}")
            )
        page.update()

    def admin_login_ui(e):
        password_input.value = ""
        page.controls.clear()
        page.add(
            ft.Text("POWERPOPS", size=40, weight="bold", text_align="center", font_family="Calisto MT"),
            ft.Text("Admin Login", size=20, weight="bold"),
            password_input,
            ft.ElevatedButton("Back", on_click=navigate_home, style=button_style),
            ft.ElevatedButton("Login", on_click=admin_section, style=button_style)
        )
        page.update()

    def resource_login_ui(e):
        password_input.value = ""
        page.controls.clear()
        page.add(
            ft.Text("POWERPOPS", size=40, weight="bold", text_align="center", font_family="Calisto MT"),
            ft.Text("Resource Access", size=20, weight="bold"),
            password_input,
            ft.ElevatedButton("Back", on_click=navigate_home, style=button_style),
            ft.ElevatedButton("Login", on_click=resource_section, style=button_style)
        )
        page.update()

    def admin_section(e):
        if password_input.value == "ANGCUTEMO":
            page.controls.clear()
            page.add(
                ft.Text("Admin Section", size=20, weight="bold"),
                ft.Text("Resources"),
                resource_ui,
                ft.Text("Reservations"),
                reservations_ui,
                ft.ElevatedButton("Back", on_click=navigate_home, style=button_style)
            )
            show_resource_ui()
            show_reservations_ui()
        else:
            password_input.error_text = "Incorrect password"
        page.update()

    def resource_section(e):
        if password_input.value == "ANGCUTEMO":
            page.controls.clear()
            page.add(
                ft.Text("Resource Management", size=20, weight="bold"),
                resource_name, resource_description, add_resource_button, resource_ui,
                ft.ElevatedButton("Back", on_click=navigate_home, style=button_style)
            )
            show_resource_ui()
        else:
            password_input.error_text = "Incorrect password"
        page.update()

    resource_ui = ft.Column()
    reservations_ui = ft.Column()
    list_ui = ft.Column()
    password_input = ft.TextField(label="Password", password=True)

    resource_name = ft.TextField(label="Resource Name")
    resource_description = ft.TextField(label="Description")
    add_resource_button = ft.ElevatedButton("Add Resource", on_click=add_resource_ui, style=button_style)

    reserve_resource_id = ft.TextField(label="Resource ID")
    reserve_user_name = ft.TextField(label="Your Name")
    reserve_date = ft.TextField(label="Date (YYYY-MM-DD)")
    reserve_feedback = ft.Text(value="", color="red")
    reserve_button = ft.ElevatedButton("Reserve", on_click=reserve_resource_ui, style=button_style)

    def reserve_section(e):
        page.controls.clear()
        page.add(
            ft.Text("POWERPOPS", size=40, weight="bold", text_align="center", font_family="Calisto MT"),
            ft.Text("Reservation Functionality", size=20, weight="bold"),
            reserve_resource_id, reserve_user_name, reserve_date, reserve_button, reserve_feedback,
            ft.ElevatedButton("Back", on_click=navigate_home, style=button_style)
        )
        page.update()

    def list_section(e):
        page.controls.clear()
        page.add(
            ft.Text("POWERPOPS", size=40, weight="bold", text_align="center", font_family="Calisto MT"),
            ft.Text("List of Resources and Reservations", size=20, weight="bold"),
            list_ui,
            ft.ElevatedButton("Back", on_click=navigate_home, style=button_style)
        )
        show_list_ui()

    def navigate_home(e):
        page.controls.clear()
        page.add(
            ft.Container(
                ft.Column([
                    ft.Text("POWERPOPS", size=40, weight="bold", text_align="center", font_family="Calisto MT"),
                    ft.ElevatedButton("Resource", on_click=resource_login_ui, expand=True, style=button_style),
                    ft.ElevatedButton("Reserve", on_click=reserve_section, expand=True, style=button_style),
                    ft.ElevatedButton("List", on_click=list_section, expand=True, style=button_style),
                    ft.ElevatedButton("Admin", on_click=admin_login_ui, expand=True, style=button_style)
                ], alignment=" center", spacing=20),
                
                padding=50
            )
        )
        page.update()

    # Navigate to home page initially
    navigate_home(None)

ft.app(target=main)

