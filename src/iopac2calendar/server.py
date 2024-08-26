from aiohttp import web


class Server:
    def __init__(self, port: int, ics_file: str | None = None, ics_path: str | None = None) -> None:
        self.port = port
        self.ics_file = ics_file
        self.server = web.Application()
        self.server.router.add_get(ics_path, self.ics_handle)
        self.server.router.add_get("/health", self.health_check)
        self.runner = web.AppRunner(self.server)

    async def ics_handle(self, *_):
        return web.FileResponse(self.ics_file)

    async def health_check(self, *_):
        return web.Response(text="OK")

    async def start(self) -> None:
        await self.runner.setup()
        site = web.TCPSite(self.runner, port=self.port)
        await site.start()

    async def stop(self) -> None:
        await self.runner.cleanup()
        self.runner = None
