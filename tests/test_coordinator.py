import pytest

@pytest.mark.asyncio
async def test_import():
    import custom_components.ternopil_grid  # noqa
