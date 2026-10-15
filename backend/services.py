from __future__ import annotations
import json 
import uuid

from datetime import date , datetime
from pathlib import Path

from .database import get_connection , init_db , seed_if_empty






# def _parse_date(value : str) -> date :
#     try:
#         return date.fromisoformat(value)
#     except ValueError as e:
#         raise ValueError(f"Invalid date format: {value}") from e



# def _night_between(check_in : str , check_out : str) -> int:
#     start = _parse_date(check_in)
#     end = _parse_date(check_out)

#     nights = (end - start).days
#     if nights < 1:
#         raise ValueError("Check-out date must be after check-in date")
#     return nights





class TravelService:
    def __init__(self . db_path : Path |None = None):
        self.db_path = db_path
        with get_connection(self.db_path) as conn:
            init_db(conn)
            seed_if_empty(conn)




    
    