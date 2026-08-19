import pytest

BATCH_PAYLOAD = {
    "СтатусЗакрытия": False,
    "ПредставлениеЗаданияНаСмену": "Изготовить 1000 болтов М10",
    "РабочийЦентр": "Цех №1",
    "Смена": "1 смена",
    "Бригада": "Бригада Иванова",
    "НомерПартии": 22222,
    "ДатаПартии": "2026-08-18",
    "Номенклатура": "Болт М10х50",
    "КодЕКН": "EKN-12345",
    "ИдентификаторРЦ": "RC-001",
    "ДатаВремяНачалаСмены": "2026-08-18T08:00:00",
    "ДатаВремяОкончанияСмены": "2026-08-18T20:00:00",
}


@pytest.mark.asyncio
async def test_create_batch_returns_201_and_full_response(client):
    response = await client.post("/api/v1/batches", json=[BATCH_PAYLOAD])

    assert response.status_code == 201
    body = response.json()
    assert len(body) == 1
    assert body[0]["batch_number"] == 22222
    assert body[0]["is_closed"] is False
    assert body[0]["products"] == []


@pytest.mark.asyncio
async def test_create_batch_duplicate_returns_409(client):
    await client.post("/api/v1/batches", json=[BATCH_PAYLOAD])

    response = await client.post("/api/v1/batches", json=[BATCH_PAYLOAD])

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_batch_not_found_returns_404(client):
    response = await client.get("/api/v1/batches/999999")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_batch_closing_sets_closed_at(client):
    create_resp = await client.post("/api/v1/batches", json=[BATCH_PAYLOAD])
    batch_id = create_resp.json()[0]["id"]

    response = await client.patch(
        f"/api/v1/batches/{batch_id}",
        json={"СтатусЗакрытия": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_closed"] is True
    assert body["closed_at"] is not None


@pytest.mark.asyncio
async def test_list_batches_filters_by_is_closed(client):
    await client.post("/api/v1/batches", json=[BATCH_PAYLOAD])

    response = await client.get("/api/v1/batches", params={"is_closed": False})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert all(item["is_closed"] is False for item in body["items"])
