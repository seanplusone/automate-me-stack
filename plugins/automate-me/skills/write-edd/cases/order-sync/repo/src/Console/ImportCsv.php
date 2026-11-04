<?php

namespace App\Console;

use App\Framework\DB;

class ImportCsv
{
    protected $signature = 'app:orders:import-csv';

    public function handle($rows)
    {
        foreach ($rows as $row) {
            DB::table('orders')->insert([
                'site_name' => $row[0],
                'status' => $row[1],
                'notes' => $row[2],
            ]);
        }
    }
}
