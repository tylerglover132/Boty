class User:
    def __init__(self, dist_id: int, name: str, points: int) -> None:
        self.dist_id = dist_id
        self.name = name
        self.points = points

class TriviaScore:
    def __init__(self, name: str, points: int):
        self.name = name
        self.points = points