"""工具设备台账接口测试：登记、保养周期提醒、报废与删除保护。"""

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
            "assignee": "测试员",
            "location": "测试仓库",
            "maintenance_cycle": "每月",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_equipment_create_and_list(client, equipment):
    assert equipment["code"].startswith("GJ-")
    assert equipment["status"] == "在用"
    assert equipment["available_quantity"] == 2
    # 未登记保养时，下次保养日期按建档时间 + 周期推算
    next_at = datetime.fromisoformat(equipment["next_maintenance_at"])
    assert 25 <= (next_at - datetime.now()).days <= 31

    listed = client.get("/api/v1/equipment", params={"keyword": "测试洗地机"}).json()
    assert listed["meta"]["total"] == 1
    assert listed["items"][0]["id"] == equipment["id"]

    by_cycle = client.get("/api/v1/equipment", params={"maintenance_cycle": "每月"}).json()
    assert by_cycle["meta"]["total"] >= 1

    duplicate = client.post(
        "/api/v1/equipment", json={"name": "重复编号", "code": equipment["code"]}
    )
    assert duplicate.status_code == 400

    updated = client.patch(
        f"/api/v1/equipment/{equipment['id']}", json={"assignee": "新使用人", "quantity": 5}
    ).json()
    assert updated["assignee"] == "新使用人"
    assert updated["available_quantity"] == 5


def test_maintenance_record_rolls_next_date(client, equipment):
    maintained_at = (datetime.now() - timedelta(days=1)).isoformat()
    response = client.post(
        f"/api/v1/equipment/{equipment['id']}/maintenances",
        json={
            "maintained_at": maintained_at,
            "operator": "李保养",
            "content": "清洗刷盘并检查电瓶",
            "replaced_parts": "刷盘",
            "cost": 66.5,
        },
    )
    assert response.status_code == 201, response.text
    detail = response.json()
    assert len(detail["maintenance_records"]) == 1
    record = detail["maintenance_records"][0]
    assert record["content"] == "清洗刷盘并检查电瓶"
    assert record["replaced_parts"] == "刷盘"
    assert record["cost"] == 66.5

    # 下次保养日期 = 保养时间 + 每月（30 天）
    next_at = datetime.fromisoformat(detail["next_maintenance_at"])
    expected = datetime.now() - timedelta(days=1) + timedelta(days=30)
    assert abs((next_at - expected).total_seconds()) < 60

    # 调整保养周期后重新推算
    updated = client.patch(
        f"/api/v1/equipment/{equipment['id']}", json={"maintenance_cycle": "每周"}
    ).json()
    next_at = datetime.fromisoformat(updated["next_maintenance_at"])
    expected = datetime.now() - timedelta(days=1) + timedelta(days=7)
    assert abs((next_at - expected).total_seconds()) < 60


def test_maintenance_reminders(client, equipment):
    # 把最近保养时间改到 40 天前（每月周期 → 已超期 10 天）
    client.post(
        f"/api/v1/equipment/{equipment['id']}/maintenances",
        json={
            "maintained_at": (datetime.now() - timedelta(days=40)).isoformat(),
            "operator": "李保养",
            "content": "月度保养",
        },
    )
    reminders = client.get("/api/v1/equipment/reminders").json()
    overdue_ids = [item["equipment_id"] for item in reminders["overdue"]]
    assert equipment["id"] in overdue_ids
    item = next(i for i in reminders["overdue"] if i["equipment_id"] == equipment["id"])
    assert item["days"] >= 9

    filtered = client.get("/api/v1/equipment", params={"due": "overdue"}).json()
    assert equipment["id"] in [row["id"] for row in filtered["items"]]

    # 登记一次新保养后超期解除
    client.post(
        f"/api/v1/equipment/{equipment['id']}/maintenances",
        json={"operator": "李保养", "content": "当日保养"},
    )
    reminders = client.get("/api/v1/equipment/reminders").json()
    assert equipment["id"] not in [i["equipment_id"] for i in reminders["overdue"]]


def test_scrap_flow_and_status(client, equipment):
    # 报废数量不能超过可用数量
    too_many = client.post(
        f"/api/v1/equipment/{equipment['id']}/scraps",
        json={"quantity": 3, "reason": "损坏", "operator": "经办人"},
    )
    assert too_many.status_code == 400

    # 部分报废：可用数量减少，状态仍为在用
    partial = client.post(
        f"/api/v1/equipment/{equipment['id']}/scraps",
        json={
            "quantity": 1,
            "reason": "电机烧毁无法修复",
            "disposal_method": "废品变卖",
            "operator": "经办人",
        },
    )
    assert partial.status_code == 201, partial.text
    detail = partial.json()
    assert detail["status"] == "在用"
    assert detail["available_quantity"] == 1
    assert detail["scrapped_quantity"] == 1
    assert detail["scrap_records"][0]["disposal_method"] == "废品变卖"

    # 全部报废后状态翻转，且不允许再保养、再报废
    final = client.post(
        f"/api/v1/equipment/{equipment['id']}/scraps",
        json={"quantity": 1, "reason": "车架断裂", "operator": "经办人"},
    ).json()
    assert final["status"] == "已报废"
    assert final["available_quantity"] == 0

    maintain = client.post(
        f"/api/v1/equipment/{equipment['id']}/maintenances",
        json={"operator": "李保养", "content": "不应成功"},
    )
    assert maintain.status_code == 400
    rescrap = client.post(
        f"/api/v1/equipment/{equipment['id']}/scraps",
        json={"quantity": 1, "reason": "重复", "operator": "经办人"},
    )
    assert rescrap.status_code == 400


def test_quantity_not_below_scrapped(client, equipment):
    client.post(
        f"/api/v1/equipment/{equipment['id']}/scraps",
        json={"quantity": 1, "reason": "损坏", "operator": "经办人"},
    )
    # 配置数量不能小于 1（校验）也不能小于已报废数量（业务规则）
    invalid = client.patch(f"/api/v1/equipment/{equipment['id']}", json={"quantity": 0})
    assert invalid.status_code == 422

    # 调减到与已报废数量持平：可用为 0，状态同步为已报废
    shrunk = client.patch(f"/api/v1/equipment/{equipment['id']}", json={"quantity": 1}).json()
    assert shrunk["available_quantity"] == 0
    assert shrunk["status"] == "已报废"

    # 补回配置数量后恢复在用
    restored = client.patch(f"/api/v1/equipment/{equipment['id']}", json={"quantity": 3}).json()
    assert restored["available_quantity"] == 2
    assert restored["status"] == "在用"


def test_equipment_delete_guard(client, equipment):
    client.post(
        f"/api/v1/equipment/{equipment['id']}/maintenances",
        json={"operator": "李保养", "content": "月度保养"},
    )
    blocked = client.delete(f"/api/v1/equipment/{equipment['id']}")
    assert blocked.status_code == 409

    ok = client.delete(f"/api/v1/equipment/{equipment['id']}", params={"force": "true"})
    assert ok.status_code == 200
    assert client.get(f"/api/v1/equipment/{equipment['id']}").status_code == 404


def test_dashboard_includes_equipment_stats(client, equipment):
    payload = client.get("/api/v1/stats/dashboard").json()
    overview = payload["overview"]
    assert overview["equipment_total"] >= 1
    assert overview["equipment_in_use"] >= 1
    assert "equipment_maintenance_overdue" in overview
    assert "equipment_maintenance_upcoming" in overview
    assert "overdue" in payload["equipment_reminders"]
    assert "upcoming" in payload["equipment_reminders"]
