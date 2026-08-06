# from textual.containers import VerticalScroll

# from widgets.status_card import StatusCard

# from services import tanks as tanks_service
# from services.refresh import refresh_manager


# class TanksPage(VerticalScroll):

#     def compose(self):

#         self.cards = {}

#         tanks = tanks_service.get_tanks()

#         for tank in tanks:

#             card = StatusCard(
#                 f"Tank {tank.tank_number}",
#                 self.get_rows(tank)
#             )

#             self.cards[tank.id] = card

#             yield card


#     def on_mount(self):

#         refresh_manager.register(
#             self.refresh_data
#         )


#     def refresh_data(self):

#         tanks = tanks_service.get_tanks()

#         for tank in tanks:

#             if tank.id in self.cards:

#                 self.cards[tank.id].update_rows(
#                     self.get_rows(tank)
#                 )


#     def get_rows(self, tank):

#         return [

#             (
#                 "Enabled",
#                 "Yes" if tank.enabled else "No"
#             ),

#             (
#                 "Capacity",
#                 f"{tank.capacity} L"
#             ),

#             (
#                 "Volume",
#                 f"{tank.volume:.1f} L"
#             ),

#             (
#                 "Ullage",
#                 f"{tank.ullage:.1f} L"
#             ),

#             (
#                 "Level",
#                 f"{tank.level} mm"
#             ),

#             (
#                 "Temperature",
#                 f"{tank.temperature:.1f} °C"
#             ),

#             (
#                 "Water",
#                 f"{tank.water:.1f} mm"
#             ),

#             (
#                 "Grade ID",
#                 str(tank.grade_id)
#             ),

#             (
#                 "Probe ID",
#                 str(tank.probe_id)
#             ),

#             (
#                 "Downloaded",
#                 "Yes" if tank.downloaded else "No"
#             ),

#         ]