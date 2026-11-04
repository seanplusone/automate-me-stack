<?php

class Order extends Model
{
    public static function forAccount($accountId)
    {
        return static::where('account_id', $accountId);
    }
}
