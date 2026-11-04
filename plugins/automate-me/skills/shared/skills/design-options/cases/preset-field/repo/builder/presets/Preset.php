<?php

// A builder palette entry that fills in an ordinary field. The runtime only ever sees the base field.
abstract class Preset
{
    public static $label;
    public static $baseField;

    public static function settings()
    {
        return [];
    }

    public static function excludedAncestors()
    {
        return [RepeaterField::$type];
    }

    public static function getDefinition(array $config)
    {
        $base = static::$baseField;
        return $base::getDefinition(array_merge(static::settings(), $config));
    }
}
