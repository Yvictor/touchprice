import pytest
from shioaji.contracts import Future
from shioaji.order import Order
from touchprice import TouchOrder, TouchOrderCond, OrderCmd, TouchCmd, StoreCond


@pytest.fixture()
def api(mocker):
    api = mocker.MagicMock()
    return api


@pytest.fixture()
def touch_order(api):
    return TouchOrder(api)


@pytest.fixture()
def contract():
    return {
        "TXFC0": Future(
            code="TXFC0",
            symbol="TXF202003",
            name="臺股期貨",
            category="TXF",
            delivery_month="202003",
            underlying_kind="I",
            limit_up=10805.0,
            limit_down=8841.0,
            reference=9823.0,
            update_date="2020/04/07",
        )
    }


@pytest.fixture()
def order():
    return Order(
        action="Buy",
        price=-1,
        quantity=1,
        order_type="ROD",
        price_type="MKT",
        octype="Auto",
    )


def test_set_condition(contract: Future, order: Order, touch_order: TouchOrder):
    condition = TouchOrderCond(
        touch_cmd=TouchCmd(code="TXFC0", price=9985.0),
        order_cmd=OrderCmd(code="TXFC0", order=order),
    )
    touch_order.contracts = contract
    touch_order.set_condition(condition)
    res = touch_order.conditions.get(condition.touch_cmd.code)
    assert res[-1].price == condition.touch_cmd.price
    assert res[-1].action == condition.order_cmd.order.action
    assert res[-1].order_contract == contract[condition.order_cmd.code]
    assert res[-1].order == condition.order_cmd.order
    assert res[-1].excuted == False
    touch_order.api.quote.subscribe.assert_called_once_with(
        touch_order.contracts[condition.touch_cmd.code]
    )


testcase_delete_condition = [["TXFC0", False], ["TXFD0", False]]


@pytest.mark.parametrize("contract_code, deleted", testcase_delete_condition)
def test_delete_condition(
    contract: Future,
    order: Order,
    touch_order: TouchOrder,
    contract_code: str,
    deleted: bool,
):
    touch_cond = TouchOrderCond(
        touch_cmd=TouchCmd(code="TXFC0", price=9985.0),
        order_cmd=OrderCmd(code="TXFC0", order=order),
    )
    cond_key = touch_cond.touch_cmd.code
    touch_order.contracts = contract
    touch_order.conditions = {
        contract_code: [
            StoreCond(
                price=touch_cond.touch_cmd.price,
                action=touch_cond.order_cmd.order.action,
                order_contract=touch_order.contracts[touch_cond.order_cmd.code],
                order=touch_cond.order_cmd.order,
                excuted=False,
            )
        ]
    }
    touch_order.delete_condition(touch_cond)
    storecode = StoreCond(
        price=touch_cond.touch_cmd.price,
        action=touch_cond.order_cmd.order.action,
        order_contract=contract[touch_cond.order_cmd.code],
        order=touch_cond.order_cmd.order,
        excuted=False,
    )
    if touch_order.conditions.get(cond_key, False):
        res = storecode in touch_order.conditions.get(cond_key)
    else:
        res = False
    assert res == deleted



testcase_touch = [[9900, True], [9985, True], [9999, False]]


@pytest.mark.parametrize("price, price_touched", testcase_touch)
def test_touch(
    contract: Future,
    order: Order,
    touch_order: TouchOrder,
    price: float,
    price_touched: bool,
):
    topic = "O/TXFC0"
    quote = {"Close": [9985.0]}
    touch_cond = TouchOrderCond(
        touch_cmd=TouchCmd(code="TXFC0", price=price),
        order_cmd=OrderCmd(code="TXFC0", order=order),
    )
    touch_key = touch_cond.touch_cmd.code
    touch_order.contracts = contract
    touch_order.conditions = {
        touch_key: [
            StoreCond(
                price=touch_cond.touch_cmd.price,
                action=touch_cond.order_cmd.order.action,
                order_contract=touch_order.contracts[touch_cond.order_cmd.code],
                order=touch_cond.order_cmd.order,
                excuted=False,
            )
        ]
    }
    touch_order.touch(topic, quote)
    res = touch_order.conditions.get(touch_key)[-1].excuted
    assert res == price_touched
    assert touch_order.api.place_order.called == price_touched
    if price_touched:
        touch_order.api.place_order.assert_called_once_with(
            touch_order.conditions[touch_key][-1].order_contract,
            touch_order.conditions[touch_key][-1].order,
        )
