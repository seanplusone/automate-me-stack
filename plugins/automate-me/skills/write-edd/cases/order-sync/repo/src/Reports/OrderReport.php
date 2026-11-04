<?php

namespace App\Reports;

use App\Models\Order;

class OrderReport
{
    public function openCount()
    {
        return Order::where('status', 'open')->count();
    }
}
