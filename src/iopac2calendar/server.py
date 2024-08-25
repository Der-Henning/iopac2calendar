from aiohttp import web


class Server:
    def __init__(self, host: str, port: int, ics_file: str | None = None, ics_path: str | None = None) -> None:
        self.host = host
        self.port = port
        self.ics_file = ics_file
        self.server = web.Application()
        self.server.router.add_get(ics_path, self.handle)
        self.runner = web.AppRunner(self.server)

    async def handle(self, *_):
        return web.FileResponse(self.ics_file)

    async def start(self) -> None:
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()

    async def stop(self) -> None:
        await self.runner.cleanup()
        self.runner = None
