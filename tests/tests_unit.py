# encoding: utf-8
#! /usr/bin/env python
import logging
import io
from datetime import datetime
import unittest

from opcua import ua
from opcua.ua import extensionobject_from_binary
from opcua.ua import extensionobject_to_binary
from opcua.ua.uatypes import flatten, get_shape, reshape
from opcua.server.internal_subscription import WhereClauseEvaluator
from opcua.common.event_objects import BaseEvent
from opcua.common.ua_utils import string_to_variant, variant_to_string, string_to_val, val_to_string



class TestUnit(unittest.TestCase):

    '''
    Simple unit test that do not need to setup a server or a client
    '''

    def test_string_to_variant_int(self):
        s_arr_uint = "[1, 2, 3, 4]"
        arr_uint = [1, 2, 3, 4]
        s_uint = "1"

        self.assertEqual(string_to_val(s_arr_uint, ua.VariantType.UInt32), arr_uint)
        self.assertEqual(string_to_val(s_arr_uint, ua.VariantType.UInt16), arr_uint)
        self.assertEqual(val_to_string(arr_uint), s_arr_uint)

    def test_string_to_variant_float(self):
        s_arr_float = "[1.1, 2.1, 3, 4.0]"
        arr_float = [1.1, 2.1, 3, 4.0]
        s_float = "1.9"
        self.assertEqual(string_to_val(s_float, ua.VariantType.Float), 1.9)
        self.assertEqual(val_to_string(arr_float), s_arr_float)

    def test_string_to_variant_datetime_string(self):
        s_arr_datetime = "[2014-05-6, 2016-10-3]"
        arr_string = ['2014-05-6', '2016-10-3']
        arr_datetime = [datetime(2014, 5, 6), datetime(2016, 10, 3)]
        s_datetime = "2014-05-3"
        self.assertEqual(val_to_string(arr_string), s_arr_datetime)
        self.assertEqual(string_to_val(s_arr_datetime, ua.VariantType.String), arr_string)
        self.assertEqual(string_to_val(s_arr_datetime, ua.VariantType.DateTime), arr_datetime )

    def test_string_to_variant_nodeid(self):
        s_arr_nodeid = "[ns=2;i=56, i=45]"
        arr_nodeid = [ua.NodeId.from_string("ns=2;i=56"), ua.NodeId.from_string("i=45")]
        s_nodeid = "i=45"
        self.assertEqual(string_to_val(s_arr_nodeid, ua.VariantType.NodeId), arr_nodeid)

    def test_string_to_variant_status_code(self):
        s_statuscode = "Good"
        statuscode = ua.StatusCode(ua.StatusCodes.Good)
        s_statuscode2 = "Uncertain"
        statuscode2 = ua.StatusCode(ua.StatusCodes.Uncertain)
        self.assertEqual(string_to_val(s_statuscode, ua.VariantType.StatusCode), statuscode)
        self.assertEqual(string_to_val(s_statuscode2, ua.VariantType.StatusCode), statuscode2)
    def test_string_to_variant_qname(self):
        string = "2:name"
        obj = ua.QualifiedName("name", 2)
        self.assertEqual(string_to_val(string, ua.VariantType.QualifiedName), obj)
        self.assertEqual(val_to_string(obj), string)

    def test_string_to_variant_localized_text(self):
        string = "_This is my string"
        #string = "_This is my nøåæ"FIXME: does not work with python2 ?!?!
        obj = ua.LocalizedText(string)
        self.assertEqual(string_to_val(string, ua.VariantType.LocalizedText), obj)
        self.assertEqual(val_to_string(obj), string)

    def test_variant_dimensions(self):
        l = [[[1.0, 1.0, 1.0, 1.0], [2.0, 2.0, 2.0, 2.0], [3.0, 3.0, 3.0, 3.0]],[[5.0, 5.0, 5.0, 5.0], [7.0, 8.0, 9.0, 01.0], [1.0, 1.0, 1.0, 1.0]]]
        v = ua.Variant(l)
        self.assertEqual(v.Dimensions, [2, 3, 4])
        v2 = ua.Variant.from_binary(ua.utils.Buffer(v.to_binary()))
        self.assertEqual(v, v2)
        self.assertEqual(v.Dimensions, v2.Dimensions)
        
        # very special case
        l = [[[], [], []], [[], [], []]]
        v = ua.Variant(l, ua.VariantType.UInt32)
        self.assertEqual(v.Dimensions, [2, 3, 0])
        v2 = ua.Variant.from_binary(ua.utils.Buffer(v.to_binary()))
        self.assertEqual(v.Dimensions, v2.Dimensions)
        self.assertEqual(v, v2)

    def test_flatten(self):
        l = [[[1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0]],[[1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0]]]
        l2 = flatten(l)
        dims = get_shape(l)
        self.assertEqual(dims, [2, 3, 4])
        self.assertNotEqual(l, l2)

        l3 = reshape(l2, (2,3,4))
        self.assertEqual(l, l3)


        l = [[[], [], []], [[], [], []]]
        l2 = flatten(l)
        dims = get_shape(l)
        self.assertEqual(dims, [2, 3, 0])

        l = [1, 2, 3, 4]
        l2 = flatten(l)
        dims = get_shape(l)
        self.assertEqual(dims, [4])
        self.assertEqual(l, l2)

    def test_custom_variant(self):
        with self.assertRaises(ua.UaError):
            v = ua.Variant(b"ljsdfljds", ua.VariantTypeCustom(89))
        v = ua.Variant(b"ljsdfljds", ua.VariantTypeCustom(61))
        v2 = ua.Variant.from_binary(ua.utils.Buffer(v.to_binary()))
        self.assertEqual(v.VariantType, v2.VariantType)
        self.assertEqual(v, v2)


    def test_custom_variant_array(self):
        v = ua.Variant([b"ljsdfljds", b"lkjsdljksdf"], ua.VariantTypeCustom(40))
        v2 = ua.Variant.from_binary(ua.utils.Buffer(v.to_binary()))
        self.assertEqual(v.VariantType, v2.VariantType)
        self.assertEqual(v, v2)

    def test_guid(self):
        g = ua.Guid()
        sc = ua.StatusCode()

    def test_nodeid(self):
        nid = ua.NodeId()
        self.assertEqual(nid.NodeIdType, ua.NodeIdType.TwoByte)
        nid = ua.NodeId(446, 3, ua.NodeIdType.FourByte)
        self.assertEqual(nid.NodeIdType, ua.NodeIdType.FourByte)
        d = nid.to_binary()
        new_nid = nid.from_binary(io.BytesIO(d))
        self.assertEqual(new_nid, nid)
        self.assertEqual(new_nid.NodeIdType, ua.NodeIdType.FourByte)
        self.assertEqual(new_nid.Identifier, 446)
        self.assertEqual(new_nid.NamespaceIndex, 3)

        tb = ua.TwoByteNodeId(53)
        fb = ua.FourByteNodeId(53)
        n = ua.NumericNodeId(53)
        n1 = ua.NumericNodeId(53, 0)
        s = ua.StringNodeId(53, 0)  # should we raise an exception???
        s1 = ua.StringNodeId("53", 0)
        bs = ua.ByteStringNodeId(b"53", 0)
        gid = ua.Guid()
        g = ua.ByteStringNodeId(gid, 0)
        guid = ua.GuidNodeId(gid)
        self.assertEqual(tb, fb)
        self.assertEqual(tb, n)
        self.assertEqual(tb, n1)
        self.assertEqual(n1, fb)
        self.assertNotEqual(n1, s)
        self.assertNotEqual(s, bs)
        self.assertNotEqual(s, g)
        self.assertNotEqual(g, guid)
        self.assertEqual(tb, ua.NodeId.from_binary(ua.utils.Buffer(tb.to_binary())))
        self.assertEqual(fb, ua.NodeId.from_binary(ua.utils.Buffer(fb.to_binary())))
        self.assertEqual(n, ua.NodeId.from_binary(ua.utils.Buffer(n.to_binary())))
        self.assertEqual(s1, ua.NodeId.from_binary(ua.utils.Buffer(s1.to_binary())))
        self.assertEqual(bs, ua.NodeId.from_binary(ua.utils.Buffer(bs.to_binary())))
        self.assertEqual(guid, ua.NodeId.from_binary(ua.utils.Buffer(guid.to_binary())))

    def test_nodeid_string(self):
        nid0 = ua.NodeId(45)
        self.assertEqual(nid0, ua.NodeId.from_string("i=45"))
        self.assertEqual(nid0, ua.NodeId.from_string("ns=0;i=45"))
        nid = ua.NodeId(45, 10)
        self.assertEqual(nid, ua.NodeId.from_string("i=45; ns=10"))
        self.assertNotEqual(nid, ua.NodeId.from_string("i=45; ns=11"))
        self.assertNotEqual(nid, ua.NodeId.from_string("i=5; ns=10"))
        # not sure the next one is correct...
        self.assertEqual(nid, ua.NodeId.from_string("i=45; ns=10; srv=serverid"))
        
        nid1 = ua.NodeId("myid.mynodeid", 7)
        self.assertEqual(nid1, ua.NodeId.from_string("ns=7; s=myid.mynodeid"))
        with self.assertRaises(ua.UaError):
            nid1 = ua.NodeId(7, "myid.mynodeid")

    def test_bad_string(self):
        with self.assertRaises(ua.UaStringParsingError):
            ua.NodeId.from_string("ns=r;s=yu")
        with self.assertRaises(ua.UaStringParsingError):
            ua.NodeId.from_string("i=r;ns=1")
        with self.assertRaises(ua.UaStringParsingError):
            ua.NodeId.from_string("ns=1")
        with self.assertRaises(ua.UaError):
            ua.QualifiedName.from_string("i:yu")
        with self.assertRaises(ua.UaError):
            ua.QualifiedName.from_string("i:::yu")

    def test_expandednodeid(self):
        nid = ua.ExpandedNodeId()
        self.assertEqual(nid.NodeIdType, ua.NodeIdType.TwoByte)
        nid2 = ua.ExpandedNodeId.from_binary(ua.utils.Buffer(nid.to_binary()))
        self.assertEqual(nid, nid2)

    def test_null_string(self):
        v = ua.Variant(None, ua.VariantType.String)
        b = v.to_binary()
        v2 = ua.Variant.from_binary(ua.utils.Buffer(b))
        self.assertEqual(v.Value, v2.Value)
        v = ua.Variant("", ua.VariantType.String)
        b = v.to_binary()
        v2 = ua.Variant.from_binary(ua.utils.Buffer(b))
        self.assertEqual(v.Value, v2.Value)

    def test_extension_object(self):
        obj = ua.UserNameIdentityToken()
        obj.UserName = "admin"
        obj.Password = b"pass"
        obj2 = ua.extensionobject_from_binary(ua.utils.Buffer(extensionobject_to_binary(obj)))
        self.assertEqual(type(obj), type(obj2))
        self.assertEqual(obj.UserName, obj2.UserName)
        self.assertEqual(obj.Password, obj2.Password)
        v1 = ua.Variant(obj)
        v2 = ua.Variant.from_binary(ua.utils.Buffer(v1.to_binary()))
        self.assertEqual(type(v1), type(v2))
        self.assertEqual(v1.VariantType, v2.VariantType)

    def test_unknown_extension_object(self):
        obj = ua.ExtensionObject()
        obj.Body = b'example of data in custom format'
        obj.TypeId = ua.NodeId.from_string('ns=3;i=42')
        data = ua.utils.Buffer(extensionobject_to_binary(obj))
        obj2 = ua.extensionobject_from_binary(data)
        self.assertEqual(type(obj2), ua.ExtensionObject)
        self.assertEqual(obj2.TypeId, obj.TypeId)
        self.assertEqual(obj2.Body, b'example of data in custom format')

    def test_datetime(self):
        now = datetime.utcnow()
        epch = ua.datetime_to_win_epoch(now)
        dt = ua.win_epoch_to_datetime(epch)
        self.assertEqual(now, dt)

        # python's datetime has a range from Jan 1, 0001 to the end of year 9999
        # windows' filetime has a range from Jan 1, 1601 to approx. year 30828
        # let's test an overlapping range [Jan 1, 1601 - Dec 31, 9999]
        dt = datetime(1601, 1, 1)
        self.assertEqual(ua.win_epoch_to_datetime(ua.datetime_to_win_epoch(dt)), dt)
        dt = datetime(9999, 12, 31, 23, 59, 59)
        self.assertEqual(ua.win_epoch_to_datetime(ua.datetime_to_win_epoch(dt)), dt)

        epch = 128930364000001000
        dt = ua.win_epoch_to_datetime(epch)
        epch2 = ua.datetime_to_win_epoch(dt)
        self.assertEqual(epch, epch2)

        epch = 0
        self.assertEqual(ua.datetime_to_win_epoch(ua.win_epoch_to_datetime(epch)), epch)

    def test_equal_nodeid(self):
        nid1 = ua.NodeId(999, 2)
        nid2 = ua.NodeId(999, 2)
        self.assertTrue(nid1 == nid2)
        self.assertTrue(id(nid1) != id(nid2))

    def test_zero_nodeid(self):
        self.assertEqual(ua.NodeId(), ua.NodeId(0, 0))
        self.assertEqual(ua.NodeId(), ua.NodeId.from_string('ns=0;i=0;'))

    def test_string_nodeid(self):
        nid = ua.NodeId('titi', 1)
        self.assertEqual(nid.NamespaceIndex, 1)
        self.assertEqual(nid.Identifier, 'titi')
        self.assertEqual(nid.NodeIdType, ua.NodeIdType.String)

    def test_unicode_string_nodeid(self):
        nid = ua.NodeId('hëllò', 1)
        self.assertEqual(nid.NamespaceIndex, 1)
        self.assertEqual(nid.Identifier, 'hëllò')
        self.assertEqual(nid.NodeIdType, ua.NodeIdType.String)
        d = nid.to_binary()
        new_nid = nid.from_binary(io.BytesIO(d))
        self.assertEqual(new_nid, nid)
        self.assertEqual(new_nid.Identifier, 'hëllò')
        self.assertEqual(new_nid.NodeIdType, ua.NodeIdType.String)

    def test_numeric_nodeid(self):
        nid = ua.NodeId(999, 2)
        self.assertEqual(nid.NamespaceIndex, 2)
        self.assertEqual(nid.Identifier, 999)
        self.assertEqual(nid.NodeIdType, ua.NodeIdType.Numeric)

    def test_qualifiedstring_nodeid(self):
        nid = ua.NodeId.from_string('ns=2;s=PLC1.Manufacturer;')
        self.assertEqual(nid.NamespaceIndex, 2)
        self.assertEqual(nid.Identifier, 'PLC1.Manufacturer')

    def test_strrepr_nodeid(self):
        nid = ua.NodeId.from_string('ns=2;s=PLC1.Manufacturer;')
        self.assertEqual(nid.to_string(), 'ns=2;s=PLC1.Manufacturer')
        #self.assertEqual(repr(nid), 'ns=2;s=PLC1.Manufacturer;')

    def test_qualified_name(self):
        qn = ua.QualifiedName('qname', 2)
        self.assertEqual(qn.NamespaceIndex, 2)
        self.assertEqual(qn.Name, 'qname')
        self.assertEqual(qn.to_string(), '2:qname')

    def test_datavalue(self):
        dv = ua.DataValue(123)
        self.assertEqual(dv.Value, ua.Variant(123))
        self.assertEqual(type(dv.Value), ua.Variant)
        dv = ua.DataValue('abc')
        self.assertEqual(dv.Value, ua.Variant('abc'))
        now = datetime.utcnow()
        dv.SourceTimestamp = now

    def test_variant(self):
        dv = ua.Variant(True, ua.VariantType.Boolean)
        self.assertEqual(dv.Value, True)
        self.assertEqual(type(dv.Value), bool)
        now = datetime.utcnow()
        v = ua.Variant(now)
        self.assertEqual(v.Value, now)
        self.assertEqual(v.VariantType, ua.VariantType.DateTime)
        v2 = ua.Variant.from_binary(ua.utils.Buffer(v.to_binary()))
        self.assertEqual(v.Value, v2.Value)
        self.assertEqual(v.VariantType, v2.VariantType)
        # commonity method:
        self.assertEqual(v, ua.Variant(v))

    def test_variant_array(self):
        v = ua.Variant([1, 2, 3, 4, 5])
        self.assertEqual(v.Value[1], 2)
        # self.assertEqual(v.VarianType, ua.VariantType.Int64) # we do not care, we should aonly test for sutff that matter
        v2 = ua.Variant.from_binary(ua.utils.Buffer(v.to_binary()))
        self.assertEqual(v.Value, v2.Value)
        self.assertEqual(v.VariantType, v2.VariantType)

        now = datetime.utcnow()
        v = ua.Variant([now])
        self.assertEqual(v.Value[0], now)
        self.assertEqual(v.VariantType, ua.VariantType.DateTime)
        v2 = ua.Variant.from_binary(ua.utils.Buffer(v.to_binary()))
        self.assertEqual(v.Value, v2.Value)
        self.assertEqual(v.VariantType, v2.VariantType)

    def test_variant_array_dim(self):
        v = ua.Variant([1, 2, 3, 4, 5, 6], dimensions = [2, 3])
        self.assertEqual(v.Value[1], 2)
        v2 = ua.Variant.from_binary(ua.utils.Buffer(v.to_binary()))
        self.assertEqual(reshape(v.Value, (2,3)), v2.Value)
        self.assertEqual(v.VariantType, v2.VariantType)
        self.assertEqual(v.Dimensions, v2.Dimensions)
        self.assertEqual(v2.Dimensions, [2, 3])

    def test_text(self):
        t1 = ua.LocalizedText('Root')
        t2 = ua.LocalizedText('Root')
        t3 = ua.LocalizedText('root')
        self.assertEqual(t1, t2)
        self.assertNotEqual(t1, t3)
        t4 = ua.LocalizedText.from_binary(ua.utils.Buffer(t1.to_binary()))
        self.assertEqual(t1, t4)

    def test_message_chunk(self):
        pol = ua.SecurityPolicy()
        chunks = ua.MessageChunk.message_to_chunks(pol, b'123', 65536)
        self.assertEqual(len(chunks), 1)
        seq = 0
        for chunk in chunks:
            seq += 1
            chunk.SequenceHeader.SequenceNumber = seq
        chunk2 = ua.MessageChunk.from_binary(pol, ua.utils.Buffer(chunks[0].to_binary()))
        self.assertEqual(chunks[0].to_binary(), chunk2.to_binary())

        # for policy None, MessageChunk overhead is 12+4+8 = 24 bytes
        # Let's pack 11 bytes into 28-byte chunks. The message must be split as 4+4+3
        chunks = ua.MessageChunk.message_to_chunks(pol, b'12345678901', 28)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0].Body, b'1234')
        self.assertEqual(chunks[1].Body, b'5678')
        self.assertEqual(chunks[2].Body, b'901')
        for chunk in chunks:
            seq += 1
            chunk.SequenceHeader.SequenceNumber = seq
            self.assertTrue(len(chunk.to_binary()) <= 28)

    def test_null(self):
        n = ua.NodeId(b'000000', 0, nodeidtype=ua.NodeIdType.Guid)
        self.assertTrue(n.is_null())
        self.assertTrue(n.has_null_identifier())

        n = ua.NodeId(b'000000', 1, nodeidtype=ua.NodeIdType.Guid)
        self.assertFalse(n.is_null())
        self.assertTrue(n.has_null_identifier())

        n = ua.NodeId()
        self.assertTrue(n.is_null())
        self.assertTrue(n.has_null_identifier())

        n = ua.NodeId(0, 0)
        self.assertTrue(n.is_null())
        self.assertTrue(n.has_null_identifier())

        n = ua.NodeId("", 0)
        self.assertTrue(n.is_null())
        self.assertTrue(n.has_null_identifier())

        n = ua.TwoByteNodeId(0)
        self.assertTrue(n.is_null())
        self.assertTrue(n.has_null_identifier())

        n = ua.NodeId(0, 3)
        self.assertFalse(n.is_null())
        self.assertTrue(n.has_null_identifier())
    
    def test_where_clause(self):
        cf = ua.ContentFilter()

        el = ua.ContentFilterElement()

        op = ua.SimpleAttributeOperand()
        op.BrowsePath.append(ua.QualifiedName("property", 2))
        el.FilterOperands.append(op)

        for i in range(10):
            op = ua.LiteralOperand()
            op.Value = ua.Variant(i)
            el.FilterOperands.append(op)

        el.FilterOperator = ua.FilterOperator.InList
        cf.Elements.append(el)

        wce = WhereClauseEvaluator(logging.getLogger(__name__), None, cf)

        ev = BaseEvent()
        ev._freeze = False
        ev.property = 3

        self.assertTrue(wce.eval(ev))

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARN)

    sclt = SubHandler()
    unittest.main(verbosity=3)
