<?php

namespace App\Traits;

use App\Framework\Context;

trait TenantScoped
{
    public static function __boot_TenantScoped()
    {
        static::addGlobalScope('tenant', function ($query) {
            $query->where('tenant_id', Context::tenantId());
        });

        static::creating(function ($model) {
            if (empty($model->tenant_id)) {
                $model->tenant_id = Context::tenantId();
            }
        });
    }
}
