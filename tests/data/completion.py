def func(act: str, message: str = "hello"): ...


class BaseModel:
    def __init__(self, learning_rate: float = 1e-4, batch_size: int = 32, **kwargs):
        func(**kwargs)


class AwesomeModel(BaseModel):
    def __init__(self, loss_scale: float = 1.0, **kwargs):
        super().__init__(batch_size=16, **kwargs)
