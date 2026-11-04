<?php

namespace App\Http;

use App\Models\Order;

class OrdersController
{
    public function update($id, $input)
    {
        $order = Order::findOrFail($id);
        $order->fill($input);
        $order->save();
        return $order;
    }

    public function destroy($id)
    {
        Order::findOrFail($id)->delete();
    }
}
