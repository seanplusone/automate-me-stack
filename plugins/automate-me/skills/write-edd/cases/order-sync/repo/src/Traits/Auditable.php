<?php

namespace App\Traits;

use App\Framework\Auth;
use App\Models\AuditLog;

trait Auditable
{
    public static function __boot_Auditable()
    {
        static::saved(function ($model) {
            AuditLog::create([
                'model' => get_class($model),
                'model_id' => $model->id,
                'user_id' => Auth::id(),
                'changes' => $model->getDirty(),
            ]);
        });
    }
}
