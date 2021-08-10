/**
 * Lib: JSON.ahk
 *     JSON lib for AutoHotkey.
 * Version:
 *     v2.1.3 [updated 04/18/2016 (MM/DD/YYYY)]
 * License:
 *     WTFPL [http://wtfpl.net/]
 * Requirements:
 *     Latest version of AutoHotkey (v1.1+ or v2.0-a+)
 * Installation:
 *     Use #Include JSON.ahk or copy into a function library folder and then
 *     use #Include <JSON>
 * Links:
 *     GitHub:     - https://github.com/cocobelgica/AutoHotkey-JSON
 *     Forum Topic - http://goo.gl/r0zI8t
 *     Email:      - cocobelgica <at> gmail <dot> com
 */


/**
 * Class: JSON
 *     The JSON object contains methods for parsing JSON and converting values
 *     to JSON. Callable - NO; Instantiable - YES; Subclassable - YES;
 *     Nestable(via #Include) - NO.
 * Methods:
 *     Load() - see relevant documentation before method definition header
 *     Dump() - see relevant documentation before method definition header
 */
class JSON
{
   /**
    * Method: Load
    *     Parses a JSON string into an AHK value
    * Syntax:
    *     value := JSON.Load( text [, reviver ] )
    * Parameter(s):
    *     value      [retval] - parsed value
    *     text    [in, ByRef] - JSON formatted string
    *     reviver   [in, opt] - function object, similar to JavaScript's
    *                           JSON.parse() 'reviver' parameter
    */
   class Load extends JSON.Functor
   {
      Call(self, ByRef text, reviver:="")
      {
         this.rev := IsObject(reviver) ? reviver : false
      ; Object keys(and array indices) are temporarily stored in arrays so that
      ; we can enumerate them in the order they appear in the document/text instead
      ; of alphabetically. Skip if no reviver function is specified.
         this.keys := this.rev ? {} : false

         static quot := Chr(34), bashq := "\" . quot
              , json_value := quot . "{[01234567890-tfn"
              , json_value_or_array_closing := quot . "{[]01234567890-tfn"
              , object_key_or_object_closing := quot . "}"

         key := ""
         is_key := false
         root := {}
         stack := [root]
         next := json_value
         pos := 0

         while ((ch := SubStr(text, ++pos, 1)) != "") {
            if InStr(" `t`r`n", ch)
               continue
            if !InStr(next, ch, 1)
               this.ParseError(next, text, pos)

            holder := stack[1]
            is_array := holder.IsArray

            if InStr(",:", ch) {
               next := (is_key := !is_array && ch == ",") ? quot : json_value

            } else if InStr("}]", ch) {
               ObjRemoveAt(stack, 1)
               next := stack[1]==root ? "" : stack[1].IsArray ? ",]" : ",}"

            } else {
               if InStr("{[", ch) {
               ; Check if Array() is overridden and if its return value has
               ; the 'IsArray' property. If so, Array() will be called normally,
               ; otherwise, use a custom base object for arrays
                  static json_array := Func("Array").IsBuiltIn || ![].IsArray ? {IsArray: true} : 0
               
               ; sacrifice readability for minor(actually negligible) performance gain
                  (ch == "{")
                     ? ( is_key := true
                       , value := {}
                       , next := object_key_or_object_closing )
                  ; ch == "["
                     : ( value := json_array ? new json_array : []
                       , next := json_value_or_array_closing )
                  
                  ObjInsertAt(stack, 1, value)

                  if (this.keys)
                     this.keys[value] := []
               
               } else {
                  if (ch == quot) {
                     i := pos
                     while (i := InStr(text, quot,, i+1)) {
                        value := StrReplace(SubStr(text, pos+1, i-pos-1), "\\", "\u005c")

                        static tail := A_AhkVersion<"2" ? 0 : -1
                        if (SubStr(value, tail) != "\")
                           break
                     }

                     if (!i)
                        this.ParseError("'", text, pos)

                       value := StrReplace(value,  "\/",  "/")
                     , value := StrReplace(value, bashq, quot)
                     , value := StrReplace(value,  "\b", "`b")
                     , value := StrReplace(value,  "\f", "`f")
                     , value := StrReplace(value,  "\n", "`n")
                     , value := StrReplace(value,  "\r", "`r")
                     , value := StrReplace(value,  "\t", "`t")

                     pos := i ; update pos
                     
                     i := 0
                     while (i := InStr(value, "\",, i+1)) {
                        if !(SubStr(value, i+1, 1) == "u")
                           this.ParseError("\", text, pos - StrLen(SubStr(value, i+1)))

                        uffff := Abs("0x" . SubStr(value, i+2, 4))
                        if (A_IsUnicode || uffff < 0x100)
                           value := SubStr(value, 1, i-1) . Chr(uffff) . SubStr(value, i+6)
                     }

                     if (is_key) {
                        key := value, next := ":"
                        continue
                     }
                  
                  } else {
                     value := SubStr(text, pos, i := RegExMatch(text, "[\]\},\s]|$",, pos)-pos)

                     static number := "number", integer :="integer"
                     if value is %number%
                     {
                        if value is %integer%
                           value += 0
                     }
                     else if (value == "true" || value == "false")
                        value := %value% + 0
                     else if (value == "null")
                        value := ""
                     else
                     ; we can do more here to pinpoint the actual culprit
                     ; but that's just too much extra work.
                        this.ParseError(next, text, pos, i)

                     pos += i-1
                  }

                  next := holder==root ? "" : is_array ? ",]" : ",}"
               } ; If InStr("{[", ch) { ... } else

               is_array? key := ObjPush(holder, value) : holder[key] := value

               if (this.keys && this.keys.HasKey(holder))
                  this.keys[holder].Push(key)
            }
         
         } ; while ( ... )

         return this.rev ? this.Walk(root, "") : root[""]
      }

      ParseError(expect, ByRef text, pos, len:=1)
      {
         static quot := Chr(34), qurly := quot . "}"
         
         line := StrSplit(SubStr(text, 1, pos), "`n", "`r").Length()
         col := pos - InStr(text, "`n",, -(StrLen(text)-pos+1))
         msg := Format("{1}`n`nLine:`t{2}`nCol:`t{3}`nChar:`t{4}"
         ,     (expect == "")     ? "Extra data"
             : (expect == "'")    ? "Unterminated string starting at"
             : (expect == "\")    ? "Invalid \escape"
             : (expect == ":")    ? "Expecting ':' delimiter"
             : (expect == quot)   ? "Expecting object key enclosed in double quotes"
             : (expect == qurly)  ? "Expecting object key enclosed in double quotes or object closing '}'"
             : (expect == ",}")   ? "Expecting ',' delimiter or object closing '}'"
             : (expect == ",]")   ? "Expecting ',' delimiter or array closing ']'"
             : InStr(expect, "]") ? "Expecting JSON value or array closing ']'"
             :                      "Expecting JSON value(string, number, true, false, null, object or array)"
         , line, col, pos)

         static offset := A_AhkVersion<"2" ? -3 : -4
         throw Exception(msg, offset, SubStr(text, pos, len))
      }

      Walk(holder, key)
      {
         value := holder[key]
         if IsObject(value) {
            for i, k in this.keys[value] {
               ; check if ObjHasKey(value, k) ??
               v := this.Walk(value, k)
               if (v != JSON.Undefined)
                  value[k] := v
               else
                  ObjDelete(value, k)
            }
         }
         
         return this.rev.Call(holder, key, value)
      }
   }

   /**
    * Method: Dump
    *     Converts an AHK value into a JSON string
    * Syntax:
    *     str := JSON.Dump( value [, replacer, space ] )
    * Parameter(s):
    *     str        [retval] - JSON representation of an AHK value
    *     value          [in] - any value(object, string, number)
    *     replacer  [in, opt] - function object, similar to JavaScript's
    *                           JSON.stringify() 'replacer' parameter
    *     space     [in, opt] - similar to JavaScript's JSON.stringify()
    *                           'space' parameter
    */
   class Dump extends JSON.Functor
   {
      Call(self, value, replacer:="", space:="")
      {
         this.rep := IsObject(replacer) ? replacer : ""

         this.gap := ""
         if (space) {
            static integer := "integer"
            if space is %integer%
               Loop, % ((n := Abs(space))>10 ? 10 : n)
                  this.gap .= " "
            else
               this.gap := SubStr(space, 1, 10)

            this.indent := "`n"
         }

         return this.Str({"": value}, "")
      }

      Str(holder, key)
      {
         value := holder[key]

         if (this.rep)
            value := this.rep.Call(holder, key, ObjHasKey(holder, key) ? value : JSON.Undefined)

         if IsObject(value) {
         ; Check object type, skip serialization for other object types such as
         ; ComObject, Func, BoundFunc, FileObject, RegExMatchObject, Property, etc.
            static type := A_AhkVersion<"2" ? "" : Func("Type")
            if (type ? type.Call(value) == "Object" : ObjGetCapacity(value) != "") {
               if (this.gap) {
                  stepback := this.indent
                  this.indent .= this.gap
               }

               is_array := value.IsArray
            ; Array() is not overridden, rollback to old method of
            ; identifying array-like objects. Due to the use of a for-loop
            ; sparse arrays such as '[1,,3]' are detected as objects({}). 
               if (!is_array) {
                  for i in value
                     is_array := i == A_Index
                  until !is_array
               }

               str := ""
               if (is_array) {
                  Loop, % value.Length() {
                     if (this.gap)
                        str .= this.indent
                     
                     v := this.Str(value, A_Index)
                     str .= (v != "") ? v . "," : "null,"
                  }
               } else {
                  colon := this.gap ? ": " : ":"
                  for k in value {
                     v := this.Str(value, k)
                     if (v != "") {
                        if (this.gap)
                           str .= this.indent

                        str .= this.Quote(k) . colon . v . ","
                     }
                  }
               }

               if (str != "") {
                  str := RTrim(str, ",")
                  if (this.gap)
                     str .= stepback
               }

               if (this.gap)
                  this.indent := stepback

               return is_array ? "[" . str . "]" : "{" . str . "}"
            }
         
         } else ; is_number ? value : "value"
            return ObjGetCapacity([value], 1)=="" ? value : this.Quote(value)
      }

      Quote(string)
      {
         static quot := Chr(34), bashq := "\" . quot

         if (string != "") {
              string := StrReplace(string,  "\",  "\\")
            ; , string := StrReplace(string,  "/",  "\/") ; optional in ECMAScript
            , string := StrReplace(string, quot, bashq)
            , string := StrReplace(string, "`b",  "\b")
            , string := StrReplace(string, "`f",  "\f")
            , string := StrReplace(string, "`n",  "\n")
            , string := StrReplace(string, "`r",  "\r")
            , string := StrReplace(string, "`t",  "\t")

            static rx_escapable := A_AhkVersion<"2" ? "O)[^\x20-\x7e]" : "[^\x20-\x7e]"
            while RegExMatch(string, rx_escapable, m)
               string := StrReplace(string, m.Value, Format("\u{1:04x}", Ord(m.Value)))
         }

         return quot . string . quot
      }
   }

   /**
    * Property: Undefined
    *     Proxy for 'undefined' type
    * Syntax:
    *     undefined := JSON.Undefined
    * Remarks:
    *     For use with reviver and replacer functions since AutoHotkey does not
    *     have an 'undefined' type. Returning blank("") or 0 won't work since these
    *     can't be distnguished from actual JSON values. This leaves us with objects.
    *     Replacer() - the caller may return a non-serializable AHK objects such as
    *     ComObject, Func, BoundFunc, FileObject, RegExMatchObject, and Property to
    *     mimic the behavior of returning 'undefined' in JavaScript but for the sake
    *     of code readability and convenience, it's better to do 'return JSON.Undefined'.
    *     Internally, the property returns a ComObject with the variant type of VT_EMPTY.
    */
   Undefined[]
   {
      get {
         static empty := {}, vt_empty := ComObject(0, &empty, 1)
         return vt_empty
      }
   }

   class Functor
   {
      __Call(method, ByRef arg, args*)
      {
      ; When casting to Call(), use a new instance of the "function object"
      ; so as to avoid directly storing the properties(used across sub-methods)
      ; into the "function object" itself.
         if IsObject(method)
            return (new this).Call(method, arg, args*)
         else if (method == "")
            return (new this).Call(arg, args*)
      }
   }
}



Jxon_Load(ByRef src, args*)
{
	static q := Chr(34)

	key := "", is_key := false
	stack := [ tree := [] ]
	is_arr := { (tree): 1 }
	next := q . "{[01234567890-tfn"
	pos := 0
	while ( (ch := SubStr(src, ++pos, 1)) != "" )
	{
		if InStr(" `t`n`r", ch)
			continue
		if !InStr(next, ch, true)
		{
			ln := ObjLength(StrSplit(SubStr(src, 1, pos), "`n"))
			col := pos - InStr(src, "`n",, -(StrLen(src)-pos+1))

			msg := Format("{}: line {} col {} (char {})"
			,   (next == "")      ? ["Extra data", ch := SubStr(src, pos)][1]
			  : (next == "'")     ? "Unterminated string starting at"
			  : (next == "\")     ? "Invalid \escape"
			  : (next == ":")     ? "Expecting ':' delimiter"
			  : (next == q)       ? "Expecting object key enclosed in double quotes"
			  : (next == q . "}") ? "Expecting object key enclosed in double quotes or object closing '}'"
			  : (next == ",}")    ? "Expecting ',' delimiter or object closing '}'"
			  : (next == ",]")    ? "Expecting ',' delimiter or array closing ']'"
			  : [ "Expecting JSON value(string, number, [true, false, null], object or array)"
			    , ch := SubStr(src, pos, (SubStr(src, pos)~="[\]\},\s]|$")-1) ][1]
			, ln, col, pos)

			throw Exception(msg, -1, ch)
		}

		is_array := is_arr[obj := stack[1]]

		if i := InStr("{[", ch)
		{
			val := (proto := args[i]) ? new proto : {}
			is_array? ObjPush(obj, val) : obj[key] := val
			ObjInsertAt(stack, 1, val)
			
			is_arr[val] := !(is_key := ch == "{")
			next := q . (is_key ? "}" : "{[]0123456789-tfn")
		}

		else if InStr("}]", ch)
		{
			ObjRemoveAt(stack, 1)
			next := stack[1]==tree ? "" : is_arr[stack[1]] ? ",]" : ",}"
		}

		else if InStr(",:", ch)
		{
			is_key := (!is_array && ch == ",")
			next := is_key ? q : q . "{[0123456789-tfn"
		}

		else ; string | number | true | false | null
		{
			if (ch == q) ; string
			{
				i := pos
				while i := InStr(src, q,, i+1)
				{
					val := StrReplace(SubStr(src, pos+1, i-pos-1), "\\", "\u005C")
					static end := A_AhkVersion<"2" ? 0 : -1
					if (SubStr(val, end) != "\")
						break
				}
				if !i ? (pos--, next := "'") : 0
					continue

				pos := i ; update pos

				  val := StrReplace(val,    "\/",  "/")
				, val := StrReplace(val, "\" . q,    q)
				, val := StrReplace(val,    "\b", "`b")
				, val := StrReplace(val,    "\f", "`f")
				, val := StrReplace(val,    "\n", "`n")
				, val := StrReplace(val,    "\r", "`r")
				, val := StrReplace(val,    "\t", "`t")

				i := 0
				while i := InStr(val, "\",, i+1)
				{
					if (SubStr(val, i+1, 1) != "u") ? (pos -= StrLen(SubStr(val, i)), next := "\") : 0
						continue 2

					; \uXXXX - JSON unicode escape sequence
					xxxx := Abs("0x" . SubStr(val, i+2, 4))
					if (A_IsUnicode || xxxx < 0x100)
						val := SubStr(val, 1, i-1) . Chr(xxxx) . SubStr(val, i+6)
				}

				if is_key
				{
					key := val, next := ":"
					continue
				}
			}

			else ; number | true | false | null
			{
				val := SubStr(src, pos, i := RegExMatch(src, "[\]\},\s]|$",, pos)-pos)
			
			; For numerical values, numerify integers and keep floats as is.
			; I'm not yet sure if I should numerify floats in v2.0-a ...
				static number := "number", integer := "integer"
				if val is %number%
				{
					if val is %integer%
						val += 0
				}
			; in v1.1, true,false,A_PtrSize,A_IsUnicode,A_Index,A_EventInfo,
			; SOMETIMES return strings due to certain optimizations. Since it
			; is just 'SOMETIMES', numerify to be consistent w/ v2.0-a
				else if (val == "true" || val == "false")
					val := %value% + 0
			; AHK_H has built-in null, can't do 'val := %value%' where value == "null"
			; as it would raise an exception in AHK_H(overriding built-in var)
				else if (val == "null")
					val := ""
			; any other values are invalid, continue to trigger error
				else if (pos--, next := "#")
					continue
				
				pos += i-1
			}
			
			is_array? ObjPush(obj, val) : obj[key] := val
			next := obj==tree ? "" : is_array ? ",]" : ",}"
		}
	}

	return tree[1]
}

Jxon_Dump(obj, indent:="", lvl:=1)
{
	static q := Chr(34)

	if IsObject(obj)
	{
		static Type := Func("Type")
		if Type ? (Type.Call(obj) != "Object") : (ObjGetCapacity(obj) == "")
			throw Exception("Object type not supported.", -1, Format("<Object at 0x{:p}>", &obj))

		is_array := 0
		for k in obj
			is_array := k == A_Index
		until !is_array

		static integer := "integer"
		if indent is %integer%
		{
			if (indent < 0)
				throw Exception("Indent parameter must be a postive integer.", -1, indent)
			spaces := indent, indent := ""
			Loop % spaces
				indent .= " "
		}
		indt := ""
		Loop, % indent ? lvl : 0
			indt .= indent

		lvl += 1, out := "" ; Make #Warn happy
		for k, v in obj
		{
			if IsObject(k) || (k == "")
				throw Exception("Invalid object key.", -1, k ? Format("<Object at 0x{:p}>", &obj) : "<blank>")
			
			if !is_array
				out .= ( ObjGetCapacity([k], 1) ? Jxon_Dump(k) : q . k . q ) ;// key
				    .  ( indent ? ": " : ":" ) ; token + padding
			out .= Jxon_Dump(v, indent, lvl) ; value
			    .  ( indent ? ",`n" . indt : "," ) ; token + indent
		}

		if (out != "")
		{
			out := Trim(out, ",`n" . indent)
			if (indent != "")
				out := "`n" . indt . out . "`n" . SubStr(indt, StrLen(indent)+1)
		}
		
		return is_array ? "[" . out . "]" : "{" . out . "}"
	}

	; Number
	else if (ObjGetCapacity([obj], 1) == "")
		return obj

	; String (null -> not supported by AHK)
	if (obj != "")
	{
		  obj := StrReplace(obj,  "\",    "\\")
		, obj := StrReplace(obj,  "/",    "\/")
		, obj := StrReplace(obj,    q, "\" . q)
		, obj := StrReplace(obj, "`b",    "\b")
		, obj := StrReplace(obj, "`f",    "\f")
		, obj := StrReplace(obj, "`n",    "\n")
		, obj := StrReplace(obj, "`r",    "\r")
		, obj := StrReplace(obj, "`t",    "\t")

		static needle := (A_AhkVersion<"2" ? "O)" : "") . "[^\x20-\x7e]"
		while RegExMatch(obj, needle, m)
			obj := StrReplace(obj, m[0], Format("\u{:04X}", Ord(m[0])))
	}
	
	return q . obj . q
}