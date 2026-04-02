from pydantic import BaseModel


class AssetModel(BaseModel):
    id: int
    asset_name: str
    asset_type: str | None = None
