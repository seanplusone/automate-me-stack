<?php

class Invoice extends Model
{
    public static function forAccount($accountId)
    {
        return static::where('account_id', $accountId);
    }
}
