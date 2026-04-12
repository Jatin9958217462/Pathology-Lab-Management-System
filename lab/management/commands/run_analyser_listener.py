"""
Management command: python manage.py run_analyser_listener

Starts a TCP server that listens for ASTM messages from lab analysers.
Configure the analyser in Admin > Analyser Interface.
"""
from django.core.management.base import BaseCommand
from lab.analyser import ASTMTCPListener


class Command(BaseCommand):
    help = 'Start ASTM TCP listener for lab analyser machine interface'

    def add_arguments(self, parser):
        parser.add_argument('--host', default='0.0.0.0', help='Bind host')
        parser.add_argument('--port', type=int, default=4000, help='TCP port')
        parser.add_argument('--analyser', type=int, default=None, help='AnalyserInterface PK')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(
            f"Starting ASTM listener on {options['host']}:{options['port']}..."
        ))
        listener = ASTMTCPListener(
            host=options['host'],
            port=options['port'],
            analyser_pk=options.get('analyser'),
        )
        try:
            listener.start()
        except KeyboardInterrupt:
            listener.stop()
            self.stdout.write(self.style.WARNING("Listener stopped."))
