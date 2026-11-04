<?php

namespace App\Sync;

use App\Models\Order;

class CrmPull
{
    public function run($tenantId, array $records)
    {
        foreach ($records as $record) {
            Order::updateOrCreate(
                ['crm_id' => $record['id'], 'tenant_id' => $tenantId],
                [
                    'site_name' => $record['site_name'],
                    'status' => $record['status'],
                    'notes' => isset($record['notes']) ? $record['notes'] : null,
                    'ordered_at' => $record['ordered_at'],
                ]
            );
        }
    }
}
