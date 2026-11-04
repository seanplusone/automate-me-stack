<?php

namespace App\Models;

use App\Framework\Model;
use App\Traits\Auditable;
use App\Traits\TenantScoped;

class Order extends Model
{
    use TenantScoped, Auditable;

    protected $table = 'orders';
    protected $fillable = ['tenant_id', 'crm_id', 'site_name', 'status', 'notes', 'score', 'ordered_at'];

    public static function boot()
    {
        parent::boot();

        static::saving(function ($order) {
            $order->score = $order->lineItems()->count() === 0 ? 100 : 100 - $order->lineItems()->count() * 10;
        });

        static::deleting(function ($order) {
            $order->lineItems()->delete();
        });
    }

    public function lineItems()
    {
        return $this->hasMany(LineItem::class);
    }
}
