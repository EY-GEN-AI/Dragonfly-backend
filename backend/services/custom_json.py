from datetime import date, datetime


class TableDataSerializer:
    """
    A class to serialize table_data into a JSON-compatible format.
    """
    @staticmethod
    def serialize_records(records):
        return [
            {
                key: (value.isoformat() if isinstance(value, (datetime, date)) else value)
                for key, value in record.items()
            }
            for record in records
        ]