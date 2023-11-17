# iOPAC to Calendar

This tool regularly scrapes the reader account of libraries
using the iOPAC software and serves an calender file that
can be subscribed to.

## Quick Start

Prequisities: Git and Docker installed

1. Clone the repository and enter the project folder.

    ```bash
    git clone https://github.com/Der-Henning/iopac2calendar.git
    cd iopac2calendar
    ```

2. Create a `config.yaml`.

    ```yaml
    Bibliotheken:
        my-Library:
            URL: https://iopac.my-Library.de/

    Konten:
        account1:
            Bibliothek: my-Library
            Kundenummer: 123456789
            Passwort: fh4hf78
        account2:
            Bibliothek: my-Library
            Kundenummer: 987654321
            Passwort: dskdj93n3
    ```

3. Build and start the docker container.

    ```bash
    docker-compose up -d
    ```

4. The Calender will be available under `localhost:8080/iopac.ics`

I recommend running this on a small server or NAS.
To make the calender available online you should use a reverse Proxy
that adds encryption and authorization.

## Advanced options

Configure via environment variables or by creating a `.env` file.

Options:

```bash
PORT=8080           # Port of the Web Server
SLEEP_TIME=600      # Sleep time in seconds between calendar updates
ICS_FILE=iopac.ics  # Where to write the .ics file locally
ICS_PATH=/iopac.ics # Web path to serve the online calender.
                    # Relevant if you use a reverse proxy for multiple
                    # services without subdomains.
```
