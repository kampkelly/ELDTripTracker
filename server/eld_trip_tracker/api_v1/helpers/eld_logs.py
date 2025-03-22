from datetime import datetime

from api_v1.lib.logger import general_logger
from reportlab.lib.colors import blue
from reportlab.pdfgen import canvas


class ELDLog:
    def generate_log_grid(self, daily_log):
        grid = []

        for status in daily_log.duty_statuses.order_by("start_time"):
            status_start_time = datetime.combine(daily_log.date, status.start_time)
            status_end_time = datetime.combine(daily_log.date, status.end_time)

            grid.append(
                {
                    "start": status_start_time.strftime("%H:%M"),
                    "end": status_end_time.strftime("%H:%M"),
                    "status": status.status,
                    "notes": status.get_status_display(),
                }
            )

        general_logger.info(f"grid: {grid}")
        return grid

    def get_log_metadata(self, trip, entries):
        data = {
            "remarks": "Fuel stop at 07:09; Dropoff at 15:20",
            "month": datetime.now().strftime("%m"),
            "day": datetime.now().strftime("%d"),
            "year": datetime.now().strftime("%Y"),
            "office_address": "Sap",
            "home_address": "Sap",
            "from": "Los Angeles",
            "to": "Miami",
            "carrier_name": "Truck",
            "truck_no": "4568",
        }

        duty_hours = {"off_duty": 0.0, "sleeper": 0.0, "driving": 0.0, "on_duty": 0.0}

        for entry in entries:
            start = datetime.strptime(entry["start"], "%H:%M")
            end = datetime.strptime(entry["end"], "%H:%M")

            # Handle midnight crossover (e.g., 23:30 to 01:00)
            if end < start:
                end = end.replace(day=end.day + 1)

            duration = (end - start).total_seconds() / 3600  # Convert to hours
            duty_hours[entry["status"].replace("-", "_")] += duration

        total_hours = sum(duty_hours.values())
        data.update(duty_hours)
        data["total_hours"] = total_hours

        return data

    def process_entries(self, entries):
        sorted_entries = sorted(entries, key=lambda x: x["start"])
        transitions = []

        for i in range(1, len(sorted_entries)):
            prev_end = sorted_entries[i - 1]["end"]
            curr_start = sorted_entries[i]["start"]

            if prev_end == curr_start:
                transitions.append(
                    {
                        "time": prev_end,
                        "from_status": sorted_entries[i - 1]["status"],
                        "to_status": sorted_entries[i]["status"],
                    }
                )

        return sorted_entries, transitions

    def generate_eld_log(self, output_path, background_image, daily_data):
        CUSTOM_PAGE_SIZE = (513, 518)
        c = canvas.Canvas(output_path, pagesize=CUSTOM_PAGE_SIZE)
        c.drawImage(
            background_image,
            0,
            0,
            width=CUSTOM_PAGE_SIZE[0],
            height=CUSTOM_PAGE_SIZE[1],
        )

        coord = {
            "month": (179, 501),
            "day": (222, 501),
            "year": (267, 501),
            "office_address": (236, 423),
            "home_address": (236, 403),
            "off_duty_hours": (472, 324),
            "sleeper_hours": (472, 306),
            "driving_hours": (472, 290),
            "on_duty_hours": (472, 272),
            "total_hours": (472, 243),
            "from": (95, 475),
            "to": (279, 475),
            "carrier_name": (236, 445),
            "truck_no": (60, 405),
            # "": "",
            "total_miles": (67, 440),  # (x, y)
            "remarks": (88, 244),
            "grid": {
                "start_x": 65,  # Left edge of the grid
                "start_y_off_duty": 325,  # Y for "Off Duty" row
                "start_y_sleeper": 308,  # Y for "Sleeper Berth" row
                "start_y_driving": 291,  # Y for "Driving" row
                "start_y_on_duty": 274,  # Y for "On Duty" row
                "hour_width": 16.1,  # Width of each hour column
            },
        }

        c.setFont("Helvetica", 10)
        c.drawString(
            coord["total_miles"][0],
            coord["total_miles"][1],
            str(daily_data["total_miles"]),
        )
        c.drawString(coord["month"][0], coord["month"][1], str(daily_data["month"]))
        c.drawString(coord["day"][0], coord["day"][1], str(daily_data["day"]))
        c.drawString(coord["year"][0], coord["year"][1], str(daily_data["year"]))
        c.drawString(
            coord["office_address"][0],
            coord["office_address"][1],
            daily_data["office_address"],
        )
        c.drawString(
            coord["home_address"][0],
            coord["home_address"][1],
            daily_data["home_address"],
        )
        c.drawString(coord["from"][0], coord["from"][1], daily_data["from"])
        c.drawString(coord["to"][0], coord["to"][1], daily_data["to"])
        c.drawString(
            coord["carrier_name"][0],
            coord["carrier_name"][1],
            daily_data["carrier_name"],
        )
        c.drawString(coord["truck_no"][0], coord["truck_no"][1], daily_data["truck_no"])
        c.drawString(
            coord["off_duty_hours"][0],
            coord["off_duty_hours"][1],
            f"{daily_data['off_duty']:.1f}",
        )
        c.drawString(
            coord["sleeper_hours"][0],
            coord["sleeper_hours"][1],
            f"{daily_data['sleeper']:.1f}",
        )
        c.drawString(
            coord["driving_hours"][0],
            coord["driving_hours"][1],
            f"{daily_data['driving']:.1f}",
        )
        c.drawString(
            coord["on_duty_hours"][0],
            coord["on_duty_hours"][1],
            f"{daily_data['on_duty']:.1f}",
        )
        c.drawString(
            coord["total_hours"][0],
            coord["total_hours"][1],
            f"{daily_data['total_hours']:.1f}",
        )

        sorted_entries, transitions = self.process_entries(daily_data["entries"])

        # Fill in the 24-hour grid
        grid = coord["grid"]
        for entry in sorted_entries:
            # Parse start/end times (e.g., "17:41" → 17.683 hours)
            start = datetime.strptime(entry["start"], "%H:%M")
            end = datetime.strptime(entry["end"], "%H:%M")
            start_hour = start.hour + start.minute / 60
            end_hour = end.hour + end.minute / 60

            # Determine Y position based on status
            status_y = {
                "off-duty": grid["start_y_off_duty"],
                "sleeper": grid["start_y_sleeper"],
                "driving": grid["start_y_driving"],
                "on-duty": grid["start_y_on_duty"],
            }[entry["status"]]

            # Calculate X positions for the time block
            x_start = grid["start_x"] + (start_hour * grid["hour_width"])
            x_end = grid["start_x"] + (end_hour * grid["hour_width"])

            c.setStrokeColor(blue)
            c.setLineWidth(2)
            c.line(x_start, status_y, x_end, status_y)

            # Add vertical remarks at the end of each status block
            if "notes" in entry and entry["notes"]:
                remark_x = x_start + ((x_end - x_start) // 2)
                remark_y = status_y - 85  # start point below the status line

                # Rotate the canvas to write vertically
                c.saveState()
                c.translate(remark_x, remark_y)  # Move origin to the remark position
                c.rotate(90)
                c.setFont("Helvetica", 6)
                c.drawString(0, 0, entry["notes"])
                c.restoreState()  # Restore the canvas state

        # Draw vertical lines for transitions
        c.setStrokeColor(blue)
        c.setLineWidth(2)
        for transition in transitions:
            transition_time = datetime.strptime(transition["time"], "%H:%M")
            transition_hour = transition_time.hour + transition_time.minute / 60
            x_transition = grid["start_x"] + (transition_hour * grid["hour_width"])

            from_status_y = {
                "off-duty": grid["start_y_off_duty"],
                "sleeper": grid["start_y_sleeper"],
                "driving": grid["start_y_driving"],
                "on-duty": grid["start_y_on_duty"],
            }[transition["from_status"]]

            to_status_y = {
                "off-duty": grid["start_y_off_duty"],
                "sleeper": grid["start_y_sleeper"],
                "driving": grid["start_y_driving"],
                "on-duty": grid["start_y_on_duty"],
            }[transition["to_status"]]

            c.line(x_transition, from_status_y, x_transition, to_status_y)

        c.save()
