<?php

class OrderExportController
{
    public function export($accountId)
    {
        $csv = CsvWriter::download('orders.csv', ['Number', 'Customer', 'Total']);
        foreach (Order::forAccount($accountId)->cursor() as $order) {
            $csv->row([$order->number, $order->customer_name, $order->total]);
        }
    }
}
