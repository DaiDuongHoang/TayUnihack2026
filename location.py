import streamlit as st


class Location:
    def __init__(
        self,
        country: str = "Australia",
        city: str = "Sydney",
        suburb: str = None,
    ) -> None:
        self.country = country
        self.city = city
        self.suburb = suburb

    def __str__(self) -> str:
        if self.suburb:
            return f"{self.suburb}, {self.city}, {self.country}"
        else:
            return f"{self.city}, {self.country}"
