from sqlalchemy import String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AircraftMetadata(Base):
    """Aircraft metadata from OpenSky Network database."""

    __tablename__ = "aircraft_metadata"

    icao24: Mapped[str] = mapped_column(String, primary_key=True)
    registration: Mapped[str | None] = mapped_column(String)
    manufacturericao: Mapped[str | None] = mapped_column(String)
    manufacturername: Mapped[str | None] = mapped_column(String)
    model: Mapped[str | None] = mapped_column(String)
    typecode: Mapped[str | None] = mapped_column(String)
    serialnumber: Mapped[str | None] = mapped_column(String)
    linenumber: Mapped[str | None] = mapped_column(String)
    aircrafttype: Mapped[str | None] = mapped_column(String)
    operator: Mapped[str | None] = mapped_column(String)
    operatorcallsign: Mapped[str | None] = mapped_column(String)
    operatoricao: Mapped[str | None] = mapped_column(String)
    operatoriata: Mapped[str | None] = mapped_column(String)
    owner: Mapped[str | None] = mapped_column(String)
    testreg: Mapped[str | None] = mapped_column(String)
    registered: Mapped[str | None] = mapped_column(String)
    reguntil: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String)
    built: Mapped[str | None] = mapped_column(String)
    firstflightdate: Mapped[str | None] = mapped_column(String)
    seatconfiguration: Mapped[str | None] = mapped_column(String)
    engines: Mapped[str | None] = mapped_column(String)
    modes: Mapped[str | None] = mapped_column(String)
    adsb: Mapped[str | None] = mapped_column(String)
    acars: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String)
