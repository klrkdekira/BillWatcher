import uvicorn
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse

app = Starlette()


@app.route("/")
async def homepage(request):
    return PlainTextResponse("Hello")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
