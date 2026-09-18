"""工具与设备维护台账接口测试。"""

from datetime import datetime, timedelta

import pytest


@pytest.fixture
def equipment(client) -> dict:
    response = client.post(
        "/api/v1/equipment",
        json={
            "name": "测试洗地机",
            "category": "机械设备",
            "quantity": 2,
            "unit": "台",
            "custodian": "测试保管员",
            "maintenance_cycle_days": 30,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_equipment_crud_and_cycle(client, equipment, restroom):
    assert equipment["code"].startswith("SB-")
    assert equipment["status"] == "在用"
    assert equipment["maintenance_due"] == "正常"
    # 未登记保养时，下次保养日期 = 建档日期 + 保养周期
    expected = (datetime.now().date() + timedelta(days=30)).isoformat()
    assert equipment["next_maintenance_date"] == expected

    listed = client.get(
        "/api/v1/equipment", params={"keyword": "测试洗地机", "category": "机械设备"}
    ).json()
    assert listed["meta"]["total"] >= 1
    assert listed["items"][0]["maintenance_count"] == 0

    # 更新保养周期后下次保养日期随之重算
    updated = client.patch(
        f"/api/v1/equipment/{equipment['id']}",
        json={"maintenance_cycle_days": 60, "custodian": "新保管员", "restroom_id": restroom["id"]},
    ).json()
    assert updated["maintenance_cycle_days"] == 60
    assert updated["next_maintenance_date"] == (datetime.now().date() + timedelta(days=60)).isoformat()

    detail = client.get(f"/api/v1/equipment/{equipment['id']}").json()
    assert detail["custodian"] == "新保管员"
    assert detail["restroom"]["id"] == restroom["id"]
    assert detail["records"] == []

    missing_restroom = client.post(
        "/api/v1/equipment",
        json={"name": "错误设备", "restroom_id": 999999},
    )
    assert missing_restroom.status_code == 404


def test_maintenance_record_refreshes_due_date(client, equipment):
    maintained_at = datetime.now() - timedelta(days=40)
    created = client.post(
        f"/api/v1/equipment/{equipment['id']}/maintenance",
        json={
            "maintained_at": maintained_at.isoformat(),
            "content": "更换刷盘、检查电瓶",
            "replaced_parts": "刷盘×2",
            "operator": "设备员老周",
        },
    )
    assert created.status_code == 201, created.text
    detail = created.json()
    assert detail["maintenance_count"] == 1
    assert detail["records"][0]["content"] == "更换刷盘、检查电瓶"
    assert detail["records"][0]["replaced_parts"] == "刷盘×2"
    # 上次保养 40 天前 + 周期 30 天 => 已逾期 10 天
    expected_next = (maintained_at.date() + timedelta(days=30)).isoformat()
    assert detail["next_maintenance_date"] == expected_next
    assert detail["maintenance_due"] == "已逾期"
    assert detail["days_to_maintenance"] == -10

    # 列表支持按到期状态筛选
    overdue = client.get("/api/v1/equipment", params={"due": "已逾期"}).json()
    assert any(item["id"] == equipment["id"] for item in overdue["items"])

    # 再次保养后回到正常状态
    again = client.post(
        f"/api/v1/equipment/{equipment['id']}/maintenance",
        json={"content": "整机清洗保养", "operator": "设备员老周"},
    ).json()
    assert again["maintenance_due"] == "正常"
    assert again["maintenance_count"] == 2

    # 保养内容必填
    empty = client.post(
        f"/api/v1/equipment/{equipment['id']}/maintenance", json={"content": ""}
    )
    assert empty.status_code == 422


def test_scrap_flow(client, equipment):
    blocked = client.patch(
        f"/api/v1/equipment/{equipment['id']}", json={"status": "已报废"}
    )
    assert blocked.status_code == 400
    assert "报废登记" in blocked.json()["detail"]

    scrapped = client.post(
        f"/api/v1/equipment/{equipment['id']}/scrap",
        json={"reason": "电机烧毁无法修复", "disposal_method": "回收处理", "remark": "回收单 001"},
    ).json()
    assert scrapped["status"] == "已报废"
    assert scrapped["scrap_reason"] == "电机烧毁无法修复"
    assert scrapped["disposal_method"] == "回收处理"
    assert scrapped["scrap_note"] == "回收单 001"
    assert scrapped["scrapped_at"] is not None
    assert scrapped["maintenance_due"] == ""

    duplicate = client.post(
        f"/api/v1/equipment/{equipment['id']}/scrap",
        json={"reason": "重复报废", "disposal_method": "废弃处理"},
    )
    assert duplicate.status_code == 400

    maintained = client.post(
        f"/api/v1/equipment/{equipment['id']}/maintenance", json={"content": "尝试保养"}
    )
    assert maintained.status_code == 400

    edited = client.patch(f"/api/v1/equipment/{equipment['id']}", json={"custodian": "换人"})
    assert edited.status_code == 400

    # 已报废设备不再出现在保养提醒中
    reminders = client.get("/api/v1/equipment/reminders").json()
    assert all(item["id"] != equipment["id"] for item in reminders["overdue"])
    assert all(item["id"] != equipment["id"] for item in reminders["upcoming"])


def test_equipment_delete_guard(client, equipment):
    client.post(
        f"/api/v1/equipment/{equipment['id']}/maintenance",
        json={"content": "例行保养", "operator": "设备员"},
    )
    blocked = client.delete(f"/api/v1/equipment/{equipment['id']}")
    assert blocked.status_code == 409

    ok = client.delete(f"/api/v1/equipment/{equipment['id']}", params={"force": "true"})
    assert ok.status_code == 200
    assert client.get(f"/api/v1/equipment/{equipment['id']}").status_code == 404


def test_reminders_and_dictionaries(client, equipment):
    payload = client.get("/api/v1/meta/dictionaries").json()
    assert "机械设备" in payload["equipment_category"]
    assert "已报废" in payload["equipment_status"]
    assert "回收处理" in payload["disposal_method"]
    assert payload["maintenance_remind_days"] >= 1

    # 让设备进入「临近到期」：上次保养距今天 = 周期 - 3 天
    maintained_at = datetime.now() - timedelta(days=27)
    client.post(
        f"/api/v1/equipment/{equipment['id']}/maintenance",
        json={
            "maintained_at": maintained_at.isoformat(),
            "content": "例行保养",
            "operator": "设备员",
        },
    )
    reminders = client.get("/api/v1/equipment/reminders").json()
    upcoming_ids = [item["id"] for item in reminders["upcoming"]]
    assert equipment["id"] in upcoming_ids
    assert equipment["id"] not in [item["id"] for item in reminders["overdue"]]

    dashboard = client.get("/api/v1/stats/dashboard").json()
    overview = dashboard["overview"]
    assert overview["equipment_total"] >= 1
    assert overview["equipment_maintenance_upcoming"] >= 1
    assert any(item["id"] == equipment["id"] for item in dashboard["maintenance_reminders"])
