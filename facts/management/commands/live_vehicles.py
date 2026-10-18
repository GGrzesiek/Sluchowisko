from django.core.management.base import BaseCommand

from facts.live_vehicles import live_vehicles


class Command(BaseCommand):
    help = "Refresh positions from the city feed and list vehicles of a line that are on the road right now."

    def add_arguments(self, parser):
        parser.add_argument("--line", required=True)
        parser.add_argument("--route")
        parser.add_argument("--no-refresh", action="store_true")

    def handle(self, *args, line, route, no_refresh, **_):
        result = live_vehicles(line, route, refresh=not no_refresh)
        if error := result.get("cityApiError"):
            self.stderr.write(self.style.WARNING(f"City feed not refreshed: {error}"))
        vehicles = result["vehicles"]
        if not vehicles:
            self.stdout.write(self.style.WARNING(result["detail"]))
            return
        where = f" on route {route}" if route else ""
        self.stdout.write(
            f"Line {result['line']}{where}: {len(vehicles)} vehicle(s) with a position from the last "
            f"{result['maxAgeS']} s"
        )
        for v in vehicles:
            heading = f"{v['route']} -> {v['destination']}" if v["route"] else "no route"
            at = f"at {v['stop']}" if v["stop"] else "stop unknown"
            nxt = f", next {v['nextStop']}" if v["nextStop"] else ""
            self.stdout.write(f"  {v['number']:<6} {heading}, {at}{nxt}, {v['ageS']} s ago")
            self.stdout.write(f"         {v['appUrl']}")
