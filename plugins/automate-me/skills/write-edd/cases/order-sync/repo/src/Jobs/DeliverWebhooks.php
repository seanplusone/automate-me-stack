<?php

namespace App\Jobs;

use App\Framework\Context;
use App\Framework\Http;
use App\Notifications\WebhookOutbox;

class DeliverWebhooks
{
    public $tries = 3;
    public $backoff = [60, 300, 900];

    public function handle($tenantId)
    {
        Context::setTenant($tenantId);

        $rows = WebhookOutbox::where('status', WebhookOutbox::STATUS_PENDING)->orderBy('id')->get();
        foreach ($rows as $row) {
            $response = Http::post($row->target_url, $row->payload);
            $row->attempts = $row->attempts + 1;
            $row->status = $response->ok() ? WebhookOutbox::STATUS_SENT : WebhookOutbox::STATUS_FAILED;
            $row->last_error = $response->ok() ? null : $response->body();
            $row->save();
        }
    }

    public function failed($exception)
    {
        WebhookOutbox::where('status', WebhookOutbox::STATUS_PENDING)->update(['last_error' => $exception->getMessage()]);
    }
}
