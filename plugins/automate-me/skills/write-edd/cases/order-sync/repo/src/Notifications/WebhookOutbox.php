<?php

namespace App\Notifications;

use App\Framework\Model;

class WebhookOutbox extends Model
{
    protected $table = 'webhook_outbox';
    protected $fillable = ['tenant_id', 'target_url', 'payload', 'status', 'attempts', 'last_error'];

    const STATUS_PENDING = 'pending';
    const STATUS_SENT = 'sent';
    const STATUS_FAILED = 'failed';
}
