from langnet.flask_app.core import create_flask_app

from rich.pretty import pprint

pprint("Inside wsgi app.. about to call create")

app = create_flask_app()

if __name__ == "__main__":
    app.run()
