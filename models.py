import pydantic


class Bus(pydantic.BaseModel):
    busId: str
    route: str
    lat: float
    lng: float

    @pydantic.validator('lat')
    def validate_lat(cls, lat: float) -> float:
        if lat < -90 or lat > 90:
            raise ValueError('should be between -90 and 90')
        return lat

    @pydantic.validator('lng')
    def validate_lng(cls, lng: float) -> float:
        if lng < -180 or lng > 180:
            raise ValueError('should be between -180 and 180')
        return lng


class WindowBounds(pydantic.BaseModel):
    # can't init with default values cause all fields are required
    south_lat: float
    north_lat: float
    west_lng: float
    east_lng: float

    @pydantic.validator('south_lat', 'north_lat')
    def validate_lat(cls, lat: float) -> float:
        if lat < -90 or lat > 90:
            raise ValueError('should be between -90 and 90')
        return lat

    @pydantic.validator('west_lng', 'east_lng')
    def validate_lng(cls, lng: float) -> float:
        if lng < -180 or lng > 180:
            raise ValueError('should be between -180 and 180')
        return lng

    def is_inside(self, bus: Bus) -> bool:
        """Check if bus is inside bounds."""
        if self.south_lat > bus.lat or self.north_lat < bus.lat:
            return False
        if self.west_lng > bus.lng or self.east_lng < bus.lng:
            return False
        return True

    def update(self, south_lat: float, north_lat: float, west_lng: float, east_lng: float) -> None:
        self.south_lat = south_lat
        self.north_lat = north_lat
        self.west_lng = west_lng
        self.east_lng = east_lng


class NewBoundsMessage(pydantic.BaseModel):
    msgType: str
    data: WindowBounds

    @pydantic.validator('msgType')
    def validate_msg_type(cls, msg_type):
        if msg_type != 'newBounds':
            raise ValueError('msgType should be equal newBounds')
        return msg_type
