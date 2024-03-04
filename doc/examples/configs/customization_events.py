# Youwol application
from youwol.app.environment import Configuration, Customization, Events

Configuration(
    customization=Customization(
        events=Events(onLoad=lambda ctx: ctx.info("Configuration loaded"))
    )
)
