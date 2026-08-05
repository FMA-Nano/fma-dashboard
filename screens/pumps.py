from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Static


from widgets.status_card import StatusCard


from services import pumps as pumps_service
from services import tanks as tanks_service


from services.refresh import refresh_manager



class PumpsPage(VerticalScroll):


    def compose(self):

        self.tank_cards = {}
        self.pump_cards = {}

        yield Static( "[bold]Pumps[/bold]", classes="section-title" )
        with Horizontal(classes="card-row"):
            pumps = pumps_service.get_pumps()
            for pump in pumps:
                card = StatusCard( f"Pump {pump.id}", self.get_pump_rows(pump) )
                self.pump_cards[pump.id] = card
                yield card
                

        yield Static( "[bold]Tanks[/bold]", classes="section-title" )
        with Horizontal(classes="card-row"):
            tanks = tanks_service.get_tanks()
            for tank in tanks:
                card = StatusCard( f"Tank {tank.tank_number}", self.get_tank_rows(tank) )
                self.tank_cards[tank.id] = card
                yield card




    def on_mount(self):
        self.set_interval(5, self.refresh_data)
        

    def refresh_data(self):
        
        tanks = tanks_service.get_tanks()
        for tank in tanks:
            if tank.id in self.tank_cards:
                self.tank_cards[tank.id].update_rows(
                    self.get_tank_rows(tank)
                )

        pumps = pumps_service.get_pumps()
        for pump in pumps:
            if pump.id in self.pump_cards:
                self.pump_cards[pump.id].update_rows(
                    self.get_pump_rows(pump)
                )



    def get_tank_rows(self, tank):

        if tank.enabled:
            return [
                ( "Enabled       ", "[#5FD68A]Yes[/#5FD68A]" ),
                ( "Capacity      ", f"{tank.capacity} L" ),
                ( "Volume        ", f"[#5FD68A]{tank.volume:.1f} L[/#5FD68A]" ),
                ( "Ullage        ", f"{tank.ullage:.1f} L" ),
                ( "Level         ", f"[#d1ce00]{tank.level} mm[/#d1ce00]" ),
                ( "Temperature   ", f"[#E05C5C]{tank.temperature:.1f} °C[/#E05C5C]" ),
                ( "Water         ", f"[#00fff7]{tank.water:.1f} mm[/#00fff7]" ),
                ( "Probe         ", str(tank.probe_id) ),
            ]

        else:
            return [
                ( "Enabled       ", "No" ),
                ( "Capacity      ", f"{tank.capacity} L" ),
                ( "Volume        ", f"{tank.volume:.1f} L" ),
                ( "Ullage        ", f"{tank.ullage:.1f} L" ),
                ( "Level         ", f"{tank.level} mm" ),
                ( "Temperature   ", f"{tank.temperature:.1f} °C" ),
                ( "Water         ", f"{tank.water:.1f} mm" ),
                ( "Probe         ", str(tank.probe_id) ),
            ]


    def get_pump_rows(self, pump):

        return [
            ( "Status", pump.status_text ),
            ( "Pulse Rate", str(pump.pulse_rate) ),
            ( "Timeout", str(pump.pulse_timeout) ),
            ( "Auto Auth", str(pump.auto_authorize) ),
            ( "Hardware ID", str(pump.hardware_id) ),
            ( "Tank", str(pump.linked_tank) ),
        ]