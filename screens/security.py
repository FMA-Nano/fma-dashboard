from textual.containers import VerticalScroll
from textual.widgets import Static

from services import ssh


class SecurityPage(VerticalScroll):

    BINDINGS = [
        ("up", "cursor_up", "ScrollUp"),
        ("down", "cursor_down", "Scroll Down"),
    ]
    
    def compose(self):

        yield Static(
            "[bold]Security[/bold]",
            classes="page-title"
        )


        yield Static(
            "[bold]SSH Login History[/bold]",
            classes="section-title"
        )


        logs = ssh.get_ssh_history(20)


        output = ""


        # Header

        output += (
            f"{'Date':<14}"
            f"{'Time':<10}"
            f"{'Event'}\n"
        )


        output += "-" * 80 + "\n"


        for log in logs:


            description = log["description"]


            # Select icon

            if "Accepted" in description:

                icon = "  "


            elif "Failed" in description:

                icon = "⚠️ "


            elif "Disconnected" in description:

                icon = "  "


            elif "session closed" in description:

                icon = "  "

            elif "PAM" in description:
                icon = "‼️ "
                
            else:

                icon = "  "



            # Remove noisy ssh information

            description = (
                description
                .replace("sshd:", "")
                .replace("pam_unix(sshd:session):", "")
            )


            output += (
                f"{log['date']:<14}"
                f"{log['time']:<10}"
                f"{icon} {description}\n"
            )



        yield Static(
            output,
            classes="info-block"
        )
