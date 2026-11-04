<?php

namespace App\Models;

use App\Framework\Model;
use App\Framework\Storage;

class LineItem extends Model
{
    protected $table = 'line_items';

    public static function boot()
    {
        parent::boot();

        static::deleting(function ($lineItem) {
            Storage::delete($lineItem->photo_path);
        });
    }
}
