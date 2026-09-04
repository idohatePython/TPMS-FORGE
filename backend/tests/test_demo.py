from backend.app.modules.demo.router import generate_demo_tpms
from backend.app.schemas.demo import DemoTpmsRequest


def test_demo_generates_an_in_memory_stl_without_download_header() -> None:
    response = generate_demo_tpms(
        DemoTpmsRequest(
            tpms_type="gyroid",
            cell_size=8,
            cell_count=1,
            wall_thickness_mm=0.8,
            quality="fast",
        )
    )

    assert response.media_type == "model/stl"
    assert len(response.body) > 84
    assert response.headers["cache-control"] == "no-store"
    assert int(response.headers["x-tpms-vertices"]) > 0
    assert int(response.headers["x-tpms-triangles"]) > 0
    assert "content-disposition" not in response.headers


def test_demo_accepts_xyz_density_gradient_parameters() -> None:
    payload = DemoTpmsRequest(
        tpms_type="diamond",
        cell_size=8,
        cell_count=1,
        wall_thickness_mm=0.8,
        quality="fast",
        gradient_axis="z",
        gradient_start_offset=-0.5,
        gradient_end_offset=0.6,
    )

    assert payload.gradient_axis == "z"
    assert payload.gradient_start_offset == -0.5
    assert payload.gradient_end_offset == 0.6
