from __future__ import annotations

from weather_pipeline import build_weather_document, write_weather_json


def main() -> None:
    document = build_weather_document()
    output_path = write_weather_json(document)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
