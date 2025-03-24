import base64
import random
from datetime import datetime
from io import BytesIO

from api_v1.lib.logger import general_logger
from pdf2image import convert_from_bytes
from reportlab.lib.colors import blue, sandybrown
from reportlab.pdfgen import canvas


class ELDLog:
    """
    a class for generating ELD logs in PDF and image formats.
    """

    def generate_log_grid(self, daily_log):
        """
        generates a grid of duty status entries for a given daily log.

        args:
            daily_log: the daily log object.

        returns:
            a list of dictionaries, where each dictionary represents a duty status entry.
        """
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

        return grid

    def generate_eld_logs(self, trip, daily_logs):
        """
        generates ELD logs for a trip, including PDF and image formats.

        args:
            trip: the trip object.
            daily_logs: a list of daily log objects.

        returns:
            a list of dictionaries, where each dictionary represents an ELD log.
        """
        eld_logs = []
        for daily_log in daily_logs:
            general_logger.info(f"Generating ELD log for date: {daily_log.date}")
            grid = self.generate_log_grid(daily_log)
            log_data = self.get_log_metadata(trip, grid)
            log_data["entries"] = grid
            log_data["total_miles"] = round(daily_log.total_miles, 2)
            pdf_base64, img_base64 = self.generate_eld_log(
                output_path=f"outputs/daily_log_{daily_log.date}.pdf",
                background_image="blank-paper-log.png",
                daily_data=log_data,
            )

            eld_logs.append(
                {
                    "date": daily_log.date,
                    "total_miles": daily_log.total_miles,
                    "pdf_base64": pdf_base64,
                    "img_base64": img_base64,
                }
            )
            general_logger.info(
                f"ELD log generated successfully for date: {daily_log.date}"
            )

        return eld_logs

    def get_log_metadata(self, trip, entries):
        """
        gets metadata for the ELD log, such as remarks, dates, addresses, and duty hours.

        args:
            trip: the trip object.
            entries: a list of duty status entries.

        returns:
            a dictionary containing the log metadata.
        """
        data = {
            "remarks": "",
            "month": datetime.now().strftime("%m"),
            "day": datetime.now().strftime("%d"),
            "year": datetime.now().strftime("%Y"),
            "office_address": "4488 Richards Avenue Stockton, CA 95202",
            "home_address": "1037 Diane Street Arroyo Grande, CA 93420",
            "from": trip.current_location_name[:30]
            + ("..." if len(trip.current_location_name) > 30 else ""),
            "to": trip.dropoff_location_name[:30]
            + ("..." if len(trip.dropoff_location_name) > 30 else ""),
            "carrier_name": "Runor Trucks",
            "truck_no": str(random.randint(1000, 9999)),
        }

        duty_hours = {"off_duty": 0.0, "sleeper": 0.0, "driving": 0.0, "on_duty": 0.0}

        for entry in entries:
            start = datetime.strptime(entry["start"], "%H:%M")
            end = datetime.strptime(entry["end"], "%H:%M")

            # handle midnight crossover (e.g., 23:30 to 01:00)
            if end < start:
                end = end.replace(day=end.day + 1)

            duration = (end - start).total_seconds() / 3600  # convert to hours
            duty_hours[entry["status"].replace("-", "_")] += duration

        total_hours = sum(duty_hours.values())
        data.update(duty_hours)
        data["total_hours"] = total_hours

        general_logger.info(f"Log metadata: {data}")
        return data

    def process_entries(self, entries):
        """
        processes and sorts the duty status entries, identifying transitions between statuses.

        args:
            entries: a list of duty status entries.

        returns:
            a tuple containing the sorted entries and a list of transitions.
        """
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

        general_logger.info(f"Processed entries, found transitions: {transitions}")
        return sorted_entries, transitions

    def generate_eld_log(self, output_path, background_image, daily_data):
        """
        generates the ELD log PDF and image files.

        args:
            output_path: the path to save the PDF file.
            background_image: the path to the background image.
            daily_data: a dictionary containing the daily log data.

        returns:
            a tuple containing the base64 encoded PDF and image data.
        """
        custom_page_size = (513, 518)
        buffer = BytesIO()
        # c = canvas.Canvas(output_path, pagesize=CUSTOM_PAGE_SIZE)
        c = canvas.Canvas(buffer, pagesize=custom_page_size)
        c.drawImage(
            background_image,
            0,
            0,
            width=custom_page_size[0],
            height=custom_page_size[1],
        )

        coord = {
            "month": (179, 501),
            "day": (222, 501),
            "year": (267, 501),
            "office_address": (236, 420),
            "home_address": (236, 400),
            "off_duty_hours": (472, 324),
            "sleeper_hours": (472, 306),
            "driving_hours": (472, 290),
            "on_duty_hours": (472, 272),
            "total_hours": (472, 243),
            "from": (95, 475),
            "to": (279, 475),
            "carrier_name": (236, 442),
            "truck_no": (60, 405),
            # "": "",
            "total_miles": (67, 437),  # (x, y)
            "remarks": (88, 244),
            "grid": {
                "start_x": 65,  # left edge of the grid
                "start_y_off_duty": 325,  # y for "off duty" row
                "start_y_sleeper": 308,  # y for "sleeper berth" row
                "start_y_driving": 291,  # y for "driving" row
                "start_y_on_duty": 274,  # y for "on duty" row
                "hour_width": 16.1,  # width of each hour column
            },
        }

        c.setFont("Helvetica", 10)
        c.setFillColor(sandybrown)
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

        # fill in the 24-hour grid
        grid = coord["grid"]
        for entry in sorted_entries:
            # parse start/end times (e.g., "17:41" → 17.683 hours)
            start = datetime.strptime(entry["start"], "%H:%M")
            end = datetime.strptime(entry["end"], "%H:%M")
            start_hour = start.hour + start.minute / 60
            end_hour = end.hour + end.minute / 60

            # determine y position based on status
            status_y = {
                "off-duty": grid["start_y_off_duty"],
                "sleeper": grid["start_y_sleeper"],
                "driving": grid["start_y_driving"],
                "on-duty": grid["start_y_on_duty"],
            }[entry["status"]]

            # calculate x positions for the time block
            x_start = grid["start_x"] + (start_hour * grid["hour_width"])
            x_end = grid["start_x"] + (end_hour * grid["hour_width"])

            c.setStrokeColor(blue)
            c.setLineWidth(2)
            c.line(x_start, status_y, x_end, status_y)

            # add vertical remarks at the end of each status block
            if "notes" in entry and entry["notes"]:
                remark_x = x_start + ((x_end - x_start) // 2)
                remark_y = status_y - 85  # start point below the status line

                # rotate the canvas to write vertically
                c.saveState()
                c.translate(remark_x, remark_y)  # move origin to the remark position
                c.rotate(90)
                c.setFont("Helvetica", 6)
                c.drawString(0, 0, entry["notes"])
                c.restoreState()  # restore the canvas state

        # draw vertical lines for transitions
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
        pdf_value = buffer.getvalue()
        pdf_base64 = base64.b64encode(pdf_value).decode("utf-8")

        # save the PDF to a file in development
        # with open(output_path, "wb") as pdf_file:
        #     pdf_file.write(pdf_value)
        # general_logger.info(f"PDF saved to {output_path}")

        # convert PDF to image
        images = convert_from_bytes(pdf_value, fmt="png")
        img_base64 = None
        if images:
            image = images[0]
            img_buffer = BytesIO()
            image.save(img_buffer, format="PNG")
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
            general_logger.info("PDF converted to image successfully")
        else:
            img_base64 = None
            general_logger.warning("Failed to convert PDF to image")

        buffer.close()

        return pdf_base64, img_base64
