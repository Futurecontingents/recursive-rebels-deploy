__all__ = ["PropertyFinderScraper"]


def __getattr__(name: str):
    if name == "PropertyFinderScraper":
        from .scraper import PropertyFinderScraper

        return PropertyFinderScraper
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
